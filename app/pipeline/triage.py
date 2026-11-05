"""Triage = LLM classification + deterministic rules, merged.

The LLM handles what needs language understanding (category, sentiment, what's
missing). Regex handles exact-match signals and IDs. Merge policy:
- urgency signals and injection flag: union (either source can raise them)
- order IDs and amounts: regex only (LLMs hallucinate IDs; regex can't)
- priority: LLM value, but forced to P1 if a P1 signal fired (guardrail)
"""
from typing import Literal

from pydantic import BaseModel, Field

from app.runtime_settings import get_runtime
from app.llm.client import load_prompt, structured
from app.models.enums import Category, Priority, Sentiment
from app.models.schemas import Entities, TicketIn, TriageResult
from app.pipeline import triage_rules as rules


class _LLMTriage(BaseModel):
    """What we ask the model for. Smaller than TriageResult on purpose:
    don't ask an LLM for things code does better."""
    category: Category
    secondary_categories: list[Category] = []
    priority: Priority
    sentiment: Sentiment
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    urgency_signals: list[str] = []
    products: list[str] = []
    dates: list[str] = []
    missing_info: list[Literal["order_id", "product", "problem_details"]] = []
    injection_suspected: bool = False
    rationale: str = ""


def format_ticket(t: TicketIn) -> str:
    return (f"<ticket>\nChannel: {t.channel.value}\nSubject: {t.subject}\n\n{t.body}\n</ticket>")


def triage(ticket: TicketIn) -> TriageResult:
    text = f"{ticket.subject}\n{ticket.body}"
    llm = structured(
        [{"role": "system", "content": load_prompt("triage")},
         {"role": "user", "content": format_ticket(ticket)}],
        _LLMTriage, model=get_runtime()["triage_model"], purpose="triage",
    )

    rule_signals = rules.detect_signals(text)
    signals_set = set(rule_signals) | {s.lower().strip() for s in llm.urgency_signals if s.strip()}
    signals = sorted(signals_set)

    # P1 is defined by concrete evidence (safety/legal/chargeback/fraud). Regex evidence
    # forces P1; an LLM "P1" without any such evidence is downgraded to P2. On the eval
    # set, every LLM-only P1 from the 3B model was a false positive.
    injection = llm.injection_suspected or rules.detect_injection(text)
    p1_evidence = bool(set(rule_signals) & rules.P1_SIGNALS) or bool(signals_set & rules.P1_SIGNALS)
    priority = llm.priority
    if set(rule_signals) & rules.P1_SIGNALS:
        priority = Priority.P1
    elif priority == Priority.P1 and not p1_evidence:
        priority = Priority.P2

    # very_negative drives escalation, so it needs a second, independent signal.
    sentiment, score = llm.sentiment, llm.sentiment_score
    angry = rules.has_anger_cues(text, ignore_caps=injection)
    if sentiment == Sentiment.very_negative and not angry:
        sentiment, score = Sentiment.negative, max(score, -0.6)
    if angry and "anger" not in signals:
        signals.append("anger")

    order_ids = rules.extract_order_ids(text)
    missing = [m for m in llm.missing_info if not (m == "order_id" and order_ids)]

    return TriageResult(
        language=rules.detect_language(text),
        category=llm.category,
        secondary_categories=[c for c in llm.secondary_categories if c != llm.category],
        priority=priority,
        sentiment=sentiment,
        sentiment_score=score,
        urgency_signals=signals,
        entities=Entities(order_ids=order_ids, products=llm.products, dates=llm.dates,
                          amounts=rules.extract_amounts(text)),
        missing_info=missing,
        injection_suspected=injection,
        rationale=llm.rationale,
    )
