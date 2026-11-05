"""Human-in-the-loop gate: decides ready_to_send vs. in_review vs. escalated.
Thresholds come from runtime settings (admin-editable)."""
from datetime import date, timedelta

from app.agent.agent import AgentResult
from app.services import mock_backend as backend
from app.models.enums import RecommendedAction, TicketStatus
from app.models.schemas import TriageResult
from app.runtime_settings import get_runtime


def gate(triage: TriageResult, agent: AgentResult) -> tuple[TicketStatus, list[str]]:
    rt = get_runtime()
    low_risk, min_conf = set(rt["low_risk_categories"]), rt["auto_send_confidence"]
    out = agent.output
    reasons: list[str] = []

    if out.recommended_action == RecommendedAction.escalate:
        return TicketStatus.escalated, ["agent escalated"]

    if not rt["auto_send_enabled"]:
        reasons.append("auto-send disabled by admin")
    categories = {triage.category.value, *(c.value for c in triage.secondary_categories)}
    if not categories <= low_risk:
        reasons.append(f"category not low-risk: {sorted(categories - low_risk)}")
    if out.confidence < min_conf:
        reasons.append(f"confidence {out.confidence:.2f} < {min_conf}")
    if out.recommended_action != RecommendedAction.send:
        reasons.append(f"agent recommended {out.recommended_action.value}")
    if agent.guardrail_flags:
        reasons.append(f"guardrails: {agent.guardrail_flags}")
    if triage.injection_suspected:
        reasons.append("suspected prompt injection")
    reasons += human_actions_required(agent)
    reasons += policy_review_reasons(triage, agent)

    return (TicketStatus.in_review if reasons else TicketStatus.ready_to_send), reasons


# Signals (triage_rules) whose request needs a decision or action only a person can take.
ALWAYS_REVIEW_SIGNALS = {
    "account_recovery": "2FA/lockout recovery: identity verification needs a human (KB-026)",
    "account_change_request": "request to change the login email to a given address: never done via ticket (KB-027)",
    "churn_risk": "churn risk (repeat contact or cancellation threat): needs a human touch",
    "promo_adjustment": "retroactive promo/discount = manual price adjustment",
}


def _traced_orders(agent: AgentResult) -> list[dict]:
    return [c.result for c in agent.trace
            if c.tool == "get_order" and isinstance(c.result, dict) and "error" not in c.result]


def policy_review_reasons(triage: TriageResult, agent: AgentResult) -> list[str]:
    """Second deterministic layer, added after the full eval found 5 confident, wrong auto-sends
    (EV-27/28/29/44/49). Model confidence is not a safety signal: these were all at 0.9-1.0."""
    signals = set(triage.urgency_signals)
    reasons = [why for sig, why in ALWAYS_REVIEW_SIGNALS.items() if sig in signals]
    orders = _traced_orders(agent)
    if "address_change" in signals:
        reasons += [f"{o['id']} is {o['status']}: address can't be changed by a reply (KB-016)"
                    for o in orders if o.get("status") != "processing"]
    if "warranty_claim" in signals:
        for o in orders:
            w = o.get("warranty") or {}
            if w.get("applies") and not w.get("in_warranty"):
                reasons.append(f"{o['id']} out of warranty: any exception is a human decision (KB-024)")
            elif w.get("applies"):
                reasons.append(f"{o['id']} warranty claim: replacement must be issued by a human (KB-024)")
    return reasons


LATE_TRACE_BUSINESS_DAYS = 5  # KB-014: 5+ business days past ETA -> support opens a carrier trace


def business_days_between(start: date, end: date) -> int:
    days, d = 0, start
    while d < end:
        d += timedelta(days=1)
        if d.weekday() < 5:
            days += 1
    return days


def human_actions_required(agent: AgentResult) -> list[str]:
    """Deterministic policy checks on the order data the agent saw. Some situations need an
    action only a person can take (carrier trace, reshipment), so a draft must never be
    auto-sent for them, however confident the model is. Found by the eval (EV-14, EV-15)."""
    today = backend.today()
    reasons = []
    for c in agent.trace:
        if c.tool != "get_order" or not isinstance(c.result, dict) or "error" in c.result:
            continue
        o, oid = c.result, c.result.get("id")
        if o.get("status") == "lost":
            reasons.append(f"{oid} lost: reship/refund needs a human (KB-015)")
        eta = (o.get("tracking") or {}).get("eta")
        if o.get("status") in ("shipped", "in_transit") and eta:
            late = business_days_between(date.fromisoformat(eta), today)
            if late >= LATE_TRACE_BUSINESS_DAYS:
                reasons.append(f"{oid} {late} business days late: carrier trace needs a human (KB-014)")
    return reasons


STATUS_TO_ACTION = {
    TicketStatus.ready_to_send: RecommendedAction.send,
    TicketStatus.in_review: RecommendedAction.human_review,
    TicketStatus.escalated: RecommendedAction.escalate,
}
