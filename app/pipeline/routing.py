"""Hard-coded routing rules. No LLM. Every escalation has a named, testable reason.

Rules run BEFORE the agent: if any fires, the agent never sees the ticket.
"""
from app.runtime_settings import DEFAULT_TEAM_ROUTING, RULE_ORDER, SIGNAL_ORDER, get_runtime
from app.models.enums import Category, Priority, Sentiment
from app.models.schemas import RoutingDecision, RuleHit, TicketIn, TriageResult
from app.services import mock_backend as backend

LANG_NAME = {"en": "English", "ar": "Arabic", "mixed": "Arabic + English", "ar_latn": "Arabizi (Arabic in Latin letters)"}


def route(ticket: TicketIn, triage: TriageResult) -> RoutingDecision:
    rt = get_runtime()
    threshold, very_neg = rt["refund_escalation_threshold"], rt["very_negative_sentiment"]
    hits: list[RuleHit] = []
    signals = set(triage.urgency_signals)

    if triage.priority == Priority.P1:
        hits.append(RuleHit(rule="priority_p1", detail="Ticket triaged as P1."))
    for sig in ("legal", "chargeback"):
        if sig in signals:
            hits.append(RuleHit(rule=f"{sig}_language", detail=f"'{sig}' signal detected in ticket text."))

    categories = {triage.category, *triage.secondary_categories}
    if Category.refund in categories:
        order_totals = [o.total for oid in triage.entities.order_ids if (o := backend.find_order(oid))]
        biggest = max([*triage.entities.amounts, *order_totals], default=0.0)
        if biggest > threshold:
            hits.append(RuleHit(rule="refund_over_threshold",
                                detail=f"Refund amount ${biggest:.2f} > ${threshold:.0f}."))

    if triage.sentiment == Sentiment.very_negative and triage.sentiment_score <= very_neg:
        hits.append(RuleHit(rule="very_negative_sentiment",
                            detail=f"Sentiment {triage.sentiment_score:.2f} with anger cues."))

    cust = backend.find_customer(ticket.customer_email)
    if cust and cust.is_vip:
        hits.append(RuleHit(rule="vip_customer", detail=f"{cust.name} is VIP ({cust.plan.value})."))

    return RoutingDecision(escalate=bool(hits), hits=hits, team=assign_team(triage, hits))


def assign_team(triage: TriageResult, hits: list[RuleHit]) -> str:
    """Most severe first: the first matching key owns the ticket. Order is fixed in code;
    the key -> team mapping is admin-editable (runtime setting `team_routing`)."""
    m = get_runtime().get("team_routing") or DEFAULT_TEAM_ROUTING
    signals, rules = set(triage.urgency_signals), {h.rule for h in hits}
    for sig in SIGNAL_ORDER:
        if sig in signals:
            return m["signals"].get(sig, DEFAULT_TEAM_ROUTING["signals"][sig])
    for rule in RULE_ORDER:
        if rule in rules:
            return m["rules"].get(rule, DEFAULT_TEAM_ROUTING["rules"][rule])
    cat = triage.category.value
    return m["categories"].get(cat, DEFAULT_TEAM_ROUTING["categories"][cat])


def escalation_summary(ticket: TicketIn, triage: TriageResult, decision: RoutingDecision) -> str:
    cust = backend.find_customer(ticket.customer_email)
    who = f"{cust.name} ({cust.plan.value}, {cust.tenure_months} mo{', VIP' if cust.is_vip else ''})" \
        if cust else f"{ticket.customer_email} (not found in CRM)"
    lines = [
        f"Team: {decision.team}",
        f"Customer: {who}",
        f"Issue: [{triage.category.value}/{triage.priority.value}] {ticket.subject}",
        f"Language: {LANG_NAME[triage.language]}",
        f"Why escalated: " + "; ".join(h.detail for h in decision.hits),
        f"Sentiment: {triage.sentiment.value} ({triage.sentiment_score:+.2f})",
        f"Signals: {', '.join(triage.urgency_signals) or 'none'}",
        f"Orders: {', '.join(triage.entities.order_ids) or 'none given'}",
    ]
    if triage.injection_suspected:
        lines.append("WARNING: ticket contains a suspected prompt-injection attempt.")
    return "\n".join(lines)
