"""Routing rules are deterministic, so they get exhaustive unit tests (no LLM)."""
from app.models.enums import Category, Priority, Sentiment
from app.models.schemas import Entities, TicketIn, TriageResult
from app.pipeline.routing import route


def tri(**kw) -> TriageResult:
    base = dict(category=Category.technical, priority=Priority.P3, sentiment=Sentiment.neutral,
                sentiment_score=0.0)
    return TriageResult(**{**base, **kw})


def tk(email="omar.khalil@example.com") -> TicketIn:
    return TicketIn(subject="s", body="b", customer_email=email)


def rules(decision) -> set[str]:
    return {h.rule for h in decision.hits}


def test_clean_ticket_not_escalated():
    assert route(tk(), tri()).escalate is False


def test_p1():
    assert "priority_p1" in rules(route(tk(), tri(priority=Priority.P1)))


def test_legal_and_chargeback():
    assert "legal_language" in rules(route(tk(), tri(urgency_signals=["legal"])))
    assert "chargeback_language" in rules(route(tk(), tri(urgency_signals=["chargeback"])))


def test_refund_threshold_uses_order_total():
    over = tri(category=Category.refund, entities=Entities(order_ids=["ORD-10002"]))   # 263.99
    under = tri(category=Category.refund, entities=Entities(order_ids=["ORD-10017"]))  # 199.00
    assert "refund_over_threshold" in rules(route(tk(), over))
    assert route(tk(), under).escalate is False


def test_refund_threshold_uses_claimed_amount():
    claim = tri(category=Category.refund, entities=Entities(order_ids=["ORD-10001"], amounts=[500]))
    assert "refund_over_threshold" in rules(route(tk(), claim))


def test_refund_rule_only_for_refund_category():
    t = tri(category=Category.shipping, entities=Entities(order_ids=["ORD-10002"]))
    assert route(tk(), t).escalate is False


def test_very_negative():
    t = tri(sentiment=Sentiment.very_negative, sentiment_score=-0.9)
    assert "very_negative_sentiment" in rules(route(tk(), t))


def test_vip():
    assert "vip_customer" in rules(route(tk("sara.haddad@example.com"), tri()))


def test_team_assignment():
    assert route(tk(), tri()).team == "Technical Support"                                   # by category
    assert route(tk(), tri(category=Category.shipping)).team == "Logistics"
    assert route(tk(), tri(urgency_signals=["safety"], priority=Priority.P1)).team == "Product Safety"
    # severity order: a VIP threatening legal action goes to Legal, not VIP Care
    assert route(tk("sara.haddad@example.com"), tri(urgency_signals=["legal"])).team == "Legal & Compliance"
    assert route(tk("sara.haddad@example.com"), tri()).team == "VIP Care"
