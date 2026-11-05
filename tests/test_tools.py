"""Deterministic tests for the policy engine and tool access control (no LLM)."""
from app.agent.tools import ToolBox
from app.services import mock_backend as b


def elig(order_id):
    return b.check_refund_eligibility(b.find_order(order_id))


def test_refund_policy_edges():
    assert elig("ORD-10001")["eligible"] is True                     # 12 days, regular item
    assert elig("ORD-10003")["eligible"] is False                    # 52 days
    assert elig("ORD-10004")["eligible"] is False                    # final sale
    assert elig("ORD-10008")["type"] == "cancellation"               # processing
    assert elig("ORD-10007")["type"] == "lost_package"
    assert elig("ORD-10009")["eligible"] is False                    # in flight
    day30 = elig("ORD-10018")
    assert day30["days_since_delivery"] == 30 and day30["eligible"] is True
    assert elig("ORD-10002")["refundable_amount"] == 263.99


def test_tools_scoped_to_ticket_customer():
    tb = ToolBox("TCK-1", "omar.khalil@example.com")
    assert tb.call("get_order", {"order_id": "ORD-10001"})["id"] == "ORD-10001"       # Omar's
    assert tb.call("get_order", {"order_id": "ORD-10002"})["error"] == "access_denied"  # James's
    assert tb.call("get_customer", {"email": "sara.haddad@example.com"})["error"] == "access_denied"
    assert tb.call("get_customer", {"email": "omar.khalil@example.com"})["is_vip"] is False


def test_tool_errors_do_not_raise():
    tb = ToolBox("TCK-1", "omar.khalil@example.com")
    assert "error" in tb.call("get_order", {"wrong_arg": 1})
    assert "error" in tb.call("no_such_tool", {})
    assert len(tb.trace) == 2


def test_escalation_always_targets_current_ticket():
    tb = ToolBox("TCK-1", "omar.khalil@example.com")
    tb.call("create_escalation", {"ticket_id": "TCK-999", "reason": "x", "summary": "y"})
    assert tb.escalations[0]["ticket_id"] == "TCK-1"
