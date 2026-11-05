"""SLA logic, ticket timeline and monitoring overview (no LLM: pipeline rows inserted directly)."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth.security import hash_password
from app.db.session import engine, init_db
from app.main import app
from app.models import db
from app.models.enums import TicketStatus
from app.sla import sla_for

PW = "correct-horse-battery"
NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)


def test_sla_states():
    open_ = TicketStatus.in_review
    assert sla_for("P1", NOW - timedelta(minutes=30), open_, now=NOW)["state"] == "on_track"
    assert sla_for("P1", NOW - timedelta(minutes=50), open_, now=NOW)["state"] == "at_risk"     # > 75% of 1h
    assert sla_for("P1", NOW - timedelta(hours=2), open_, now=NOW)["state"] == "breached"
    assert sla_for("P3", NOW - timedelta(hours=2), open_, now=NOW)["state"] == "on_track"      # 24h target
    done = TicketStatus.approved
    assert sla_for("P2", NOW - timedelta(hours=3), done, resolved_at=NOW, now=NOW)["state"] == "met"
    assert sla_for("P2", NOW - timedelta(hours=5), done, resolved_at=NOW, now=NOW)["state"] == "missed"


@pytest.fixture(scope="module")
def client():
    init_db()
    created = datetime.now(timezone.utc) - timedelta(hours=3)
    with Session(engine) as s:
        if not s.exec(select(db.User).where(db.User.email == "m-lead@t.example")).first():
            s.add(db.User(email="m-lead@t.example", full_name="Lead", password_hash=hash_password(PW), role="lead",
                          team="Logistics"))
        s.add(db.Ticket(id="TCK-MON1", subject="late order", body="b", customer_email="c@x.example", channel="email",
                        created_at=created, status=TicketStatus.in_review, team="Logistics", priority="P2", language="en"))
        s.flush()
        s.add(db.Job(ticket_id="TCK-MON1", status="done", attempts=1, created_at=created,
                     locked_at=created + timedelta(seconds=2), locked_by="w1"))
        s.add(db.TriageRecord(ticket_id="TCK-MON1", result={"category": "shipping", "priority": "P2", "language": "en",
                                                           "urgency_signals": []}))
        s.add(db.PipelineRun(ticket_id="TCK-MON1", final_status=TicketStatus.in_review, total_latency_ms=60000,
                             timings_ms={"triage": 5000, "retrieve": 800, "route": 10, "agent": 54000, "hitl": 5},
                             routing={"escalate": False, "hits": [], "team": "Logistics"},
                             agent_output={"confidence": 0.7}, status_reasons=["confidence 0.70 < 0.85"],
                             created_at=created + timedelta(seconds=62)))
        s.commit()
    return TestClient(app)


def h(client):
    tok = client.post("/auth/login", data={"username": "m-lead@t.example", "password": PW}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_timeline(client):
    r = client.get("/tickets/TCK-MON1/timeline", headers=h(client))
    assert r.status_code == 200
    kinds = [e["kind"] for e in r.json()["events"]]
    assert kinds[0] == "received" and "picked_up" in kinds and "ai_triage" in kinds and "ai_agent" in kinds
    assert r.json()["sla"]["state"] == "on_track" or r.json()["sla"]["state"] == "at_risk"   # 3h of a 4h P2 target


def test_overview(client):
    r = client.get("/monitor/overview", headers=h(client))
    assert r.status_code == 200
    o = r.json()
    assert o["flow"]["received"] >= 1 and {s["stage"] for s in o["stages"]} >= {"triage", "agent"}
    assert any(t["team"] == "Logistics" and t["open"] >= 1 for t in o["teams"])
    assert [row["priority"] for row in o["sla"]] == ["P1", "P2", "P3", "P4"]


def test_list_includes_sla(client):
    rows = client.get("/tickets?status=in_review", headers=h(client)).json()
    assert all("sla" in r for r in rows) and any(r["id"] == "TCK-MON1" for r in rows)
