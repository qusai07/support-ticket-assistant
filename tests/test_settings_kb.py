"""Runtime settings and KB endpoints (no LLM; KB re-embedding is stubbed)."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth.security import hash_password
from app.db.session import engine, init_db
from app.main import app
from app.models import db
from app.models.enums import Category, Priority, Sentiment
from app.models.schemas import Entities, TicketIn, TriageResult
from app.pipeline.routing import route
from app.runtime_settings import get_runtime

PW = "correct-horse-battery"


@pytest.fixture(scope="module")
def client():
    init_db()
    with Session(engine) as s:
        for email, role, team in [("s-admin@t.example", "admin", None), ("s-lead@t.example", "lead", "Logistics"),
                                  ("s-agent@t.example", "agent", "Logistics")]:
            if not s.exec(select(db.User).where(db.User.email == email)).first():
                s.add(db.User(email=email, full_name=email, password_hash=hash_password(PW), role=role, team=team))
        s.commit()
    return TestClient(app)


def h(client, email):
    tok = client.post("/auth/login", data={"username": email, "password": PW}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_settings_change_applies_to_routing(client):
    admin = h(client, "s-admin@t.example")
    tri = TriageResult(category=Category.refund, priority=Priority.P3, sentiment=Sentiment.neutral,
                       sentiment_score=0.0, entities=Entities(order_ids=["ORD-10017"]))  # $199.00
    tk = TicketIn(subject="s", body="b", customer_email="omar.khalil@example.com")
    assert route(tk, tri).escalate is False

    r = client.patch("/settings", json={"values": {"refund_escalation_threshold": 150}}, headers=admin)
    assert r.status_code == 200
    get_runtime(force=True)
    assert "refund_over_threshold" in {x.rule for x in route(tk, tri).hits}   # no restart needed

    client.patch("/settings", json={"values": {"refund_escalation_threshold": 200}}, headers=admin)
    get_runtime(force=True)


def test_settings_validation_and_permissions(client):
    admin = h(client, "s-admin@t.example")
    bad = [{"auto_send_confidence": 2}, {"low_risk_categories": ["refund"]}, {"nope": 1},
           {"auto_send_enabled": "yes"}]
    for values in bad:
        assert client.patch("/settings", json={"values": values}, headers=admin).status_code == 422
    assert client.patch("/settings", json={"values": {"auto_send_confidence": 0.9}},
                        headers=h(client, "s-lead@t.example")).status_code == 403
    assert client.get("/settings", headers=h(client, "s-agent@t.example")).status_code == 403


def test_kb_edit_permissions(client, monkeypatch):
    import app.api.kb as kb_api
    calls = []
    monkeypatch.setattr(kb_api, "_reindex", lambda row: calls.append(row.id))
    article = {"category": "shipping", "title": "Holiday shipping cutoffs",
               "body": "Orders placed after December 20 may arrive after the holidays.",
               "title_ar": "مواعيد الشحن في العطلات", "body_ar": "الطلبات بعد 20 ديسمبر قد تصل بعد العطلات."}
    assert client.put("/kb/KB-031", json=article, headers=h(client, "s-agent@t.example")).status_code == 403
    assert client.put("/kb/bad-id", json=article, headers=h(client, "s-lead@t.example")).status_code == 422
    r = client.put("/kb/KB-031", json=article, headers=h(client, "s-lead@t.example"))
    assert r.status_code == 200 and calls == ["KB-031"]       # only the edited article is re-embedded
    assert client.get("/kb/KB-031", headers=h(client, "s-agent@t.example")).json()["title_ar"]
