"""HITL gate: deterministic 'needs a human' checks (regression for eval misses EV-14, EV-15)."""
from datetime import date

from app.agent.agent import AgentResult
from app.agent.tools import ToolBox
from app.models.enums import Category, Priority, RecommendedAction, Sentiment, TicketStatus
from app.models.schemas import AgentOutput, TriageResult
from app.pipeline.hitl import business_days_between, gate


def run_with_order(email: str, order_id: str) -> AgentResult:
    tb = ToolBox("T", email)
    tb.call("get_order", {"order_id": order_id}, step="prefetch")
    out = AgentOutput(draft_reply="Your order is on its way.", confidence=0.95,
                      recommended_action=RecommendedAction.send, sources=["KB-013"])
    return AgentResult(output=out, trace=tb.trace, escalations=[], raw_confidence=0.95)


TRI = TriageResult(category=Category.shipping, priority=Priority.P3, sentiment=Sentiment.neutral, sentiment_score=0)


def test_business_days():
    assert business_days_between(date(2026, 10, 22), date(2026, 11, 1)) == 6   # Thu -> Sun


def test_late_order_needs_human():           # EV-14: ORD-10006, 6 business days past ETA
    status, reasons = gate(TRI, run_with_order("ethan.brooks@example.com", "ORD-10006"))
    assert status == TicketStatus.in_review and any("carrier trace" in r for r in reasons)


def test_lost_order_needs_human():           # EV-15: ORD-10007 lost by carrier
    status, reasons = gate(TRI, run_with_order("lucas.moreau@example.com", "ORD-10007"))
    assert status == TicketStatus.in_review and any("lost" in r for r in reasons)


def test_on_time_order_can_auto_send():      # EV-01: ORD-10009 shipped, ETA in the future
    status, _ = gate(TRI, run_with_order("omar.khalil@example.com", "ORD-10009"))
    assert status == TicketStatus.ready_to_send
