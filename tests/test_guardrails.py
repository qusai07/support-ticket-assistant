"""Deterministic groundedness guardrails on agent drafts (no LLM)."""
from app.agent.agent import _Draft, _guardrails
from app.agent.tools import ToolBox
from app.models.schemas import RetrievedDoc, TicketIn

TICKET = TicketIn(subject="Where is my order", body="When will ORD-10009 arrive?", customer_email="omar.khalil@example.com")
KB013 = RetrievedDoc(source_id="KB-013", source_type="kb", title="Tracking",
                     snippet="Tracking can take up to 24 hours to show the first scan.", score=0.9)


def flags_for(reply: str) -> list[str]:
    tools = ToolBox("T1", TICKET.customer_email)
    tools.call("get_order", {"order_id": "ORD-10009"}, step="prefetch")   # status shipped, ETA 2026-11-04
    draft = _Draft(draft_reply=reply, confidence=0.9, recommended_action="send", sources=["KB-013"])
    return _guardrails(draft, TICKET, [KB013], tools)


def test_grounded_reply_has_no_flags():
    assert flags_for("ORD-10009 shipped; ETA 4 November 2026. Tracking can take up to 24 hours (KB-013).") == []


def test_invented_timeline_flagged():
    assert any(f.startswith("unverified_number") for f in flags_for("It arrives in 5-7 business days."))


def test_invented_url_amount_and_kb_flagged():
    f = flags_for("Print the label at www.lumora.com/label, pay $12.50, see KB-099.")
    assert any("unverified_url" in x for x in f)
    assert any("unverified_amount" in x for x in f)
    assert any("cited_unknown_kb" in x for x in f)


def test_arabic_digits_normalized():
    assert flags_for("سيصل الطلب ORD-10009 في ٤ نوفمبر 2026") == []
