"""Regression tests for the full-eval misses (2026-11-05): five confident, wrong auto-sends
(EV-27/28/29/44/49), one missed escalation (EV-59) and a Chinese-token leak in an Arabic reply.

Phrasings here are deliberately NOT copied from the eval set, so the rules are tested on
wording they were not tuned on (a rule that only matches the eval sentence is overfitting).
"""
import pytest

from app.agent.agent import FOREIGN_SCRIPT_RE, AgentResult
from app.agent.tools import ToolBox
from app.models.enums import Category, Priority, RecommendedAction, Sentiment, TicketStatus
from app.models.schemas import AgentOutput, TriageResult
from app.pipeline import triage_rules as r
from app.pipeline.hitl import gate
from app.services import mock_backend as backend


# ------------------------------------------------------------------ signals
@pytest.mark.parametrize("signal,text", [
    ("account_recovery", "I got a new phone and my authenticator app is gone, can't log in"),
    ("account_recovery", "Locked out of my account, no backup codes"),
    ("account_recovery", "ضاع جوالي وما اقدر ادخل حسابي بسبب التحقق بخطوتين"),
    ("account_change_request", "Please update the email on file to new.me@mail.com today"),
    ("account_change_request", "ابي تغيير الايميل الى ali.new@mail.com"),
    ("churn_risk", "This is the 4th time I'm reporting this. Fix it."),
    ("churn_risk", "I'll be cancelling my subscription if nobody helps"),
    ("churn_risk", "هذي ثالث مرة اكتب لكم عن نفس المشكلة"),
    ("address_change", "I typed the wrong address on ORD-10009"),
    ("address_change", "ابي اغير العنوان للطلب ORD-10008"),
    ("promo_adjustment", "I forgot to apply my coupon, can you refund the difference?"),
    ("promo_adjustment", "الكوبون ما انطبق على طلبي"),
    ("warranty_claim", "Is my watch still under warranty?"),
    ("warranty_claim", "السماعة خربت، هل عليها ضمان؟"),
])
def test_needs_person_signals(signal, text):
    assert signal in r.detect_signals(text)


@pytest.mark.parametrize("signal,text", [
    ("address_change", "How can I change the email address on my account?"),     # EV-09: self-service how-to
    ("account_change_request", "How can I change the email address on my account?"),
    ("promo_adjustment", "Can I use two promo codes on one order?"),             # EV-10: policy question
    ("account_recovery", "How do I turn on two-factor authentication?"),
    ("churn_risk", "Please cancel order ORD-10008, wrong size"),                  # order cancel != churn
])
def test_needs_person_signals_do_not_overfire(signal, text):
    assert signal not in r.detect_signals(text)


def test_strong_anger_counts_independent_cues():
    assert r.anger_cue_count("اسوأ شركة! نصابين!!") >= r.STRONG_ANGER_CUES      # EV-59 style (Egyptian)
    assert r.anger_cue_count("The camera keeps disconnecting, please help") == 0
    assert r.anger_cue_count("عذاب معكم، الطلب متأخر") == 0                       # false-positive trap


# ------------------------------------------------------------------ warranty as code
def test_warranty_expired_after_one_year():                  # EV-27: delivered 2025-03-01
    w = backend.warranty_status(backend.find_order("ORD-10019"))
    assert w["applies"] and not w["in_warranty"] and w["items"][0]["warranty_expires_on"] == "2026-03-01"


def test_warranty_business_plan_gets_two_years():
    cust = backend.find_customer("sara.haddad@example.com")   # enterprise plan
    w = backend.warranty_status(backend.find_order("ORD-10011"), cust)
    assert w["warranty_months"] == 24 and w["in_warranty"]


def test_final_sale_warranty_is_90_days():
    w = backend.warranty_status(backend.find_order("ORD-10004"))
    assert w["items"][0]["warranty_expires_on"] == "2027-01-23"


def test_get_order_tool_exposes_warranty():
    res = ToolBox("T", "lucas.moreau@example.com").get_order("ORD-10019")
    assert res["warranty"]["in_warranty"] is False


# ------------------------------------------------------------------ gate
def _run(email: str, *order_ids: str) -> AgentResult:
    tb = ToolBox("T", email)
    for oid in order_ids:
        tb.call("get_order", {"order_id": oid}, step="prefetch")
    out = AgentOutput(draft_reply="Happy to help.", confidence=1.0,
                      recommended_action=RecommendedAction.send, sources=[])
    return AgentResult(output=out, trace=tb.trace, escalations=[], raw_confidence=1.0)


def _tri(category: Category, text: str) -> TriageResult:
    return TriageResult(category=category, priority=Priority.P3, sentiment=Sentiment.neutral,
                        sentiment_score=0, urgency_signals=r.detect_signals(text))


@pytest.mark.parametrize("email,orders,category,text,why", [
    ("lucas.moreau@example.com", ["ORD-10019"], Category.technical,
     "Earbuds died, covered by warranty?", "out of warranty"),                          # EV-27
    ("maya.chen@example.com", [], Category.account,
     "Lost my phone, can't pass two-factor", "identity verification"),                  # EV-28
    ("ethan.brooks@example.com", ["ORD-10015"], Category.technical,
     "Third time asking. Camera offline again.", "churn risk"),                         # EV-29
    ("omar.khalil@example.com", ["ORD-10009"], Category.shipping,
     "Need to change the delivery address", "address can't be changed"),                # EV-44
    ("james.porter@example.com", [], Category.account,
     "Change the email on my account to x@y.org now", "never done via ticket"),         # EV-49
])
def test_confident_draft_still_needs_person(email, orders, category, text, why):
    status, reasons = gate(_tri(category, text), _run(email, *orders))
    assert status == TicketStatus.in_review and any(why in x for x in reasons), reasons


def test_address_change_before_shipping_can_auto_send():
    # ORD-10008 is still processing: the address can be changed, no human needed.
    status, _ = gate(_tri(Category.shipping, "Can I change the shipping address?"),
                     _run("rania.aziz@example.com", "ORD-10008"))
    assert status == TicketStatus.ready_to_send


def test_foreign_script_guardrail():
    assert FOREIGN_SCRIPT_RE.search("情商يا، نعتذر عن الإزعاج")                       # EV-59 draft
    assert not FOREIGN_SCRIPT_RE.search("مرحباً Omar, your order ORD-10009 ships today.")
