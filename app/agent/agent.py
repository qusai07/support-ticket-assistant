"""Tool-using agent, in two phases:

1. Tool phase: free-form chat with tool calling, up to MAX_STEPS rounds.
2. Answer phase: one constrained-JSON call that produces AgentOutput.

Small local models struggle to do tool calling and strict JSON in the same turn,
so we split them. After the agent finishes, deterministic guardrails check
groundedness and calibrate confidence. The model's self-reported confidence is
an input, not the final word.
"""
import json
import re
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from app.agent.tools import TOOL_SPECS, ToolBox
from app.config import get_settings
from app.llm.client import chat, load_prompt, structured
from app.models.enums import Category, RecommendedAction
from app.models.schemas import AgentOutput, RetrievedDoc, TicketIn, ToolCall, TriageResult
from app.pipeline.retrieval import kb_lang
from app.pipeline.triage_rules import normalize
from app.runtime_settings import get_runtime
from app.pipeline.triage import format_ticket

MAX_STEPS = 5
# Arabizi customers get English: they read it comfortably, and small models write poor Arabizi.
REPLY_LANGUAGE = {
    "en": "English",
    "ar": "Arabic (Modern Standard Arabic, friendly tone). Keep IDs like ORD-10001 and KB-006 in Latin characters.",
    "mixed": "Arabic (Modern Standard Arabic, friendly tone). Keep IDs like ORD-10001 and KB-006 in Latin characters.",
    "ar_latn": "English (the customer wrote Arabic in Latin letters; reply in simple, friendly English)",
}
KB_ID_RE = re.compile(r"\bKB-\d{3}\b")
ORDER_RE = re.compile(r"\bORD-\d{5}\b")
MONEY_RE = re.compile(r"\$\s?(\d+(?:,\d{3})*(?:\.\d{1,2})?)")
URL_RE = re.compile(r"(?:https?://|www\.)\S+")
NUM_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])")
NOT_FOUND = {"order_not_found", "customer_not_found"}  # legitimate answers, not failures


class _Draft(BaseModel):
    draft_reply: str
    clarifying_question: str | None = None
    actions_taken: list[str] = []
    sources: list[str] = Field(default=[], description="KB article IDs used, e.g. KB-006")
    confidence: float = Field(ge=0.0, le=1.0)
    recommended_action: RecommendedAction


@dataclass
class AgentResult:
    output: AgentOutput
    trace: list[ToolCall]
    escalations: list[dict]
    guardrail_flags: list[str] = field(default_factory=list)
    raw_confidence: float = 0.0


def _prefetch(tools: ToolBox, triage: TriageResult) -> None:
    """Deterministic tool calls the agent would always need. Small models skip
    'always call X' instructions, so the pipeline makes these calls itself."""
    tools.call("get_customer", {"email": tools.email}, step="prefetch")
    wants_refund = Category.refund in {triage.category, *triage.secondary_categories}
    for oid in triage.entities.order_ids[:3]:
        tools.call("get_order", {"order_id": oid}, step="prefetch")
        if wants_refund:
            tools.call("check_refund_eligibility", {"order_id": oid}, step="prefetch")


def _context_message(ticket_id: str, ticket: TicketIn, triage: TriageResult, docs: list[RetrievedDoc],
                     tools: ToolBox) -> str:
    kb = "\n\n".join(f"[{d.source_id}] {d.snippet}" for d in docs if d.source_type == "kb")
    past = "\n\n".join(f"[{d.source_id}] {d.snippet[:300]}" for d in docs if d.source_type == "past_ticket")
    facts = "\n".join(f"- {c.tool}({json.dumps(c.args)}) -> {json.dumps(c.result, default=str)}"
                      for c in tools.trace)
    reply_lang = REPLY_LANGUAGE[triage.language]
    return (
        f"Ticket ID: {ticket_id}\nCustomer email: {ticket.customer_email}\n"
        f"REPLY LANGUAGE: {reply_lang}\n"
        f"Today's date: {get_settings().reference_date}\n\n"
        f"{format_ticket(ticket)}\n\n"
        f"Triage: category={triage.category.value}, priority={triage.priority.value}, "
        f"sentiment={triage.sentiment.value}, order_ids={triage.entities.order_ids}, "
        f"missing_info={triage.missing_info}\n\n"
        f"## Tool results already fetched (verified facts)\n{facts or '(none)'}\n\n"
        f"## Help-center articles (citable)\n{kb or '(none)'}\n\n"
        f"## Similar past tickets (examples only, do not cite)\n{past or '(none)'}"
    )


def _seen_kb(docs: list[RetrievedDoc], tools: ToolBox) -> set[str]:
    """KB IDs the agent actually saw: retrieved articles + IDs inside tool results."""
    return {d.source_id for d in docs if d.source_type == "kb"} | set(KB_ID_RE.findall(tools.observed_text()))


def _guardrails(draft: _Draft, ticket: TicketIn, docs: list[RetrievedDoc], tools: ToolBox) -> list[str]:
    """Every KB ID, order ID and dollar amount in the reply must trace to a source."""
    observed = tools.observed_text() + "\n" + "\n".join(d.snippet for d in docs)
    ticket_text = f"{ticket.subject}\n{ticket.body}"
    allowed_kb = _seen_kb(docs, tools)
    flags = []

    # KB IDs written in the reply itself must be ones the agent actually saw.
    # (Unseen IDs in the `sources` metadata list are dropped later, not flagged.)
    if bad := set(KB_ID_RE.findall(draft.draft_reply)) - allowed_kb:
        flags.append(f"cited_unknown_kb:{sorted(bad)}")

    for url in URL_RE.findall(draft.draft_reply):
        if url.rstrip(".,)") not in observed:
            flags.append(f"unverified_url:{url}")

    if bad := set(ORDER_RE.findall(draft.draft_reply)) - set(ORDER_RE.findall(observed + ticket_text)):
        flags.append(f"unverified_order_id:{sorted(bad)}")

    for amt in MONEY_RE.findall(draft.draft_reply):
        v = float(amt.replace(",", ""))
        variants = {f"{v:.2f}", f"{v:g}", f"{v:.1f}"}
        if not any(x in observed for x in variants):
            flags.append(f"unverified_amount:${amt}")

    # Any other number (days, hours, percentages) must also come from evidence or the ticket.
    # Catches invented timelines like "5-7 business days" when the policy says 3-7.
    def nums(text: str) -> set[str]:
        return {(n.lstrip("0") or "0") for n in NUM_RE.findall(normalize(text)) if len(n) < 6}  # skip tracking #s

    scrubbed = MONEY_RE.sub(" ", ORDER_RE.sub(" ", KB_ID_RE.sub(" ", draft.draft_reply)))
    if bad := sorted(nums(scrubbed) - nums(observed + "\n" + ticket_text)):
        flags.append(f"unverified_number:{bad}")

    if tools.escalations and draft.recommended_action != RecommendedAction.escalate:
        flags.append("escalation_created_but_not_recommended")
    return flags


def _calibrate(draft: _Draft, flags: list[str], tools: ToolBox) -> float:
    conf = draft.confidence
    if flags:
        conf = min(conf, 0.5)
    def failed(c: ToolCall) -> bool:
        if c.error:
            return True
        return isinstance(c.result, dict) and c.result.get("error") not in (None, *NOT_FOUND)

    if any(failed(c) for c in tools.trace):
        conf = min(conf, 0.7)
    # An answer must rest on something: a cited KB article or verified order/policy data.
    grounding_tools = {"get_order", "check_refund_eligibility", "search_kb"}
    data_grounded = any(c.tool in grounding_tools and not failed(c) and
                        not (isinstance(c.result, dict) and "error" in c.result) for c in tools.trace)
    if not draft.sources and not data_grounded and not draft.clarifying_question:
        conf = min(conf, 0.75)
    return round(conf, 2)


def run_agent(ticket_id: str, ticket: TicketIn, triage: TriageResult, docs: list[RetrievedDoc]) -> AgentResult:
    model = get_runtime()["agent_model"]
    tools = ToolBox(ticket_id, ticket.customer_email, kb_lang=kb_lang(triage.language))
    _prefetch(tools, triage)
    messages: list = [
        {"role": "system", "content": load_prompt("agent")},
        {"role": "user", "content": _context_message(ticket_id, ticket, triage, docs, tools)},
    ]

    # ---- phase 1: tool use
    for _ in range(MAX_STEPS):
        resp = chat(messages, model=model, purpose="agent", tools=TOOL_SPECS)
        messages.append(resp.message)
        if not resp.message.tool_calls:
            break
        for tc in resp.message.tool_calls:
            result = tools.call(tc.function.name, dict(tc.function.arguments or {}))
            messages.append({"role": "tool", "tool_name": tc.function.name,
                             "content": json.dumps(result, default=str)})

    # ---- phase 2: structured answer
    messages.append({"role": "user", "content": (
        "Now write the final answer as JSON. draft_reply = the full message to the customer. "
        "sources = IDs of every help-center article whose information you used (e.g. KB-013 if you "
        "mention tracking scan times). actions_taken = tools you used and what they showed. "
        "confidence = how sure you are that the reply is correct and complete (0-1). "
        "recommended_action = 'send' if safe to send as is, 'human_review' if a human should check it, "
        "'escalate' if a specialist must take over.")})
    draft = structured(messages, _Draft, model=model, purpose="agent")

    flags = _guardrails(draft, ticket, docs, tools)
    action = RecommendedAction.escalate if tools.escalations else draft.recommended_action
    seen_kb = _seen_kb(docs, tools)
    output = AgentOutput(
        draft_reply=draft.draft_reply, clarifying_question=draft.clarifying_question,
        actions_taken=draft.actions_taken,
        sources=sorted({s for s in draft.sources if KB_ID_RE.fullmatch(s) and s in seen_kb}
                       | (set(KB_ID_RE.findall(draft.draft_reply)) & seen_kb)),
        confidence=_calibrate(draft, flags, tools), recommended_action=action,
    )
    return AgentResult(output=output, trace=tools.trace, escalations=tools.escalations,
                       guardrail_flags=flags, raw_confidence=draft.confidence)
