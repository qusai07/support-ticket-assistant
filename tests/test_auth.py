"""Auth, RBAC and team scoping through the real API (no LLM: tickets are inserted directly)."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth.permissions import Permission, Role, has_permission
from app.auth.security import hash_password
from app.db.session import engine, init_db
from app.main import app
from app.models import db
from app.models.enums import TicketStatus

PW = "correct-horse-battery"


@pytest.fixture(scope="module")
def client():
    init_db()
    with Session(engine) as s:
        for email, role, team in [("admin@t.example", "admin", None),
                                  ("lead@t.example", "lead", "Technical Support"),
                                  ("tech@t.example", "agent", "Technical Support"),
                                  ("refunds@t.example", "agent", "Returns & Refunds"),
                                  ("analyst@t.example", "analyst", None)]:
            s.add(db.User(email=email, full_name=email.split("@")[0], password_hash=hash_password(PW),
                          role=role, team=team))
        s.add(db.Ticket(id="TCK-TECH", subject="cam offline", body="b", customer_email="c@x.example",
                        channel="email", created_at=db._now(), status=TicketStatus.in_review,
                        team="Technical Support"))
        s.add(db.Ticket(id="TCK-ESC", subject="smoke", body="b", customer_email="c@x.example",
                        channel="email", created_at=db._now(), status=TicketStatus.escalated,
                        team="Technical Support"))
        s.add(db.Ticket(id="TCK-REF", subject="refund", body="b", customer_email="c@x.example",
                        channel="email", created_at=db._now(), status=TicketStatus.in_review,
                        team="Returns & Refunds"))
        s.commit()
    return TestClient(app)  # no `with`: skips lifespan (no Chroma/Ollama needed)


def login(client, email, password=PW):
    return client.post("/auth/login", data={"username": email, "password": password})


def h(client, email):
    return {"Authorization": f"Bearer {login(client, email).json()['access_token']}"}


def test_permission_matrix():
    assert all(has_permission(Role.admin, p) for p in Permission)
    assert not has_permission(Role.agent, Permission.USERS_MANAGE)
    assert not has_permission(Role.agent, Permission.TICKETS_HANDLE_ESCALATED)
    assert not has_permission(Role.analyst, Permission.TICKETS_REVIEW)
    assert has_permission(Role.lead, Permission.TICKETS_REASSIGN)


def test_login_and_me(client):
    assert login(client, "tech@t.example", "wrong-password").status_code == 401
    assert login(client, "nobody@t.example").status_code == 401           # same error: no user enumeration
    me = client.get("/auth/me", headers=h(client, "tech@t.example")).json()
    assert me["role"] == "agent" and "tickets:review" in me["permissions"]


def test_requires_auth(client):
    assert client.get("/tickets").status_code == 401
    assert client.get("/tickets", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_team_scoping(client):
    tech = {t["id"] for t in client.get("/tickets", headers=h(client, "tech@t.example")).json()}
    assert tech == {"TCK-TECH", "TCK-ESC"}
    assert client.get("/tickets/TCK-REF", headers=h(client, "tech@t.example")).status_code == 404  # 404, not 403
    everything = {t["id"] for t in client.get("/tickets", headers=h(client, "analyst@t.example")).json()}
    assert {"TCK-TECH", "TCK-ESC", "TCK-REF"} <= everything


def test_review_permissions(client):
    body = {"decision": "reject", "comment": "test"}
    assert client.post("/tickets/TCK-TECH/review", json=body, headers=h(client, "analyst@t.example")).status_code == 403
    assert client.post("/tickets/TCK-ESC/review", json=body, headers=h(client, "tech@t.example")).status_code == 403
    assert client.post("/tickets/TCK-TECH/review", json=body, headers=h(client, "tech@t.example")).status_code == 200
    assert client.post("/tickets/TCK-TECH/review", json=body, headers=h(client, "tech@t.example")).status_code == 409


def test_reassign_and_audit(client):
    assert client.post("/tickets/TCK-REF/assign", json={"team": "Logistics"},
                       headers=h(client, "tech@t.example")).status_code == 403
    r = client.post("/tickets/TCK-REF/assign", json={"team": "Technical Support"}, headers=h(client, "lead@t.example"))
    assert r.status_code == 200
    # the tech agent can now see it
    assert client.get("/tickets/TCK-REF", headers=h(client, "tech@t.example")).status_code == 200
    log = client.get("/users/audit", headers=h(client, "admin@t.example")).json()
    assert any(e["action"] == "ticket.assign" and e["target_id"] == "TCK-REF" for e in log)
    assert client.get("/users/audit", headers=h(client, "lead@t.example")).status_code == 403


def test_refresh_rotation_and_reuse_detection(client, monkeypatch):
    import app.auth.router as auth_router
    pair = login(client, "tech@t.example").json()
    new = client.post("/auth/refresh", json={"refresh_token": pair["refresh_token"]})
    assert new.status_code == 200
    # within the grace window (two tabs racing): rejected, but other sessions survive
    assert client.post("/auth/refresh", json={"refresh_token": pair["refresh_token"]}).status_code == 401
    newer = client.post("/auth/refresh", json={"refresh_token": new.json()["refresh_token"]})
    assert newer.status_code == 200
    # after the grace window, reuse is treated as theft: all sessions revoked
    monkeypatch.setattr(auth_router, "REUSE_GRACE_S", 0)
    assert client.post("/auth/refresh", json={"refresh_token": pair["refresh_token"]}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": newer.json()["refresh_token"]}).status_code == 401


def test_user_admin(client):
    admin = h(client, "admin@t.example")
    body = {"email": "new@t.example", "full_name": "New", "password": "a-long-password", "role": "agent"}
    assert client.post("/users", json=body, headers=admin).status_code == 422          # agent needs a team
    r = client.post("/users", json={**body, "team": "Logistics"}, headers=admin)
    assert r.status_code == 201
    uid = r.json()["id"]
    assert client.post("/users", json={**body, "team": "Logistics"}, headers=admin).status_code == 409
    assert client.post("/users", json={**body, "team": "Logistics"},
                       headers=h(client, "lead@t.example")).status_code == 403
    # deactivated users can't log in
    client.patch(f"/users/{uid}", json={"is_active": False}, headers=admin)
    assert login(client, "new@t.example", "a-long-password").status_code == 401
    # admin can't lock themselves out
    me = client.get("/auth/me", headers=admin).json()
    assert client.patch(f"/users/{me['id']}", json={"is_active": False}, headers=admin).status_code == 400
