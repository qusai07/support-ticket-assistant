"""Admin: editable role permissions, teams, routing rules (no LLM)."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth.permissions import Permission, has_permission, invalidate_cache, seed_teams
from app.auth.security import hash_password
from app.db.session import engine, init_db
from app.main import app
from app.models import db
from app.models.enums import Category, Priority, Sentiment
from app.models.schemas import TriageResult
from app.pipeline.routing import assign_team
from app.runtime_settings import get_runtime

PW = "correct-horse-battery"


@pytest.fixture(scope="module")
def client():
    init_db()
    seed_teams()
    with Session(engine) as s:
        for email, role, team in [("a-admin@t.example", "admin", None), ("a-agent@t.example", "agent", "Logistics")]:
            if not s.exec(select(db.User).where(db.User.email == email)).first():
                s.add(db.User(email=email, full_name=email, password_hash=hash_password(PW), role=role, team=team))
        s.commit()
    return TestClient(app)


def h(client, email):
    tok = client.post("/auth/login", data={"username": email, "password": PW}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_edit_role_permissions_takes_effect(client):
    admin = h(client, "a-admin@t.example")
    assert not has_permission("agent", Permission.KB_MANAGE)
    r = client.put("/admin/roles/agent", headers=admin,
                   json={"permissions": ["tickets:view", "tickets:create", "tickets:review", "kb:manage"]})
    assert r.status_code == 200
    assert has_permission("agent", Permission.KB_MANAGE)                    # no restart
    assert client.post("/admin/roles/agent/reset", headers=admin).status_code == 200
    assert not has_permission("agent", Permission.KB_MANAGE)


def test_admin_role_is_locked_and_view_required(client):
    admin = h(client, "a-admin@t.example")
    assert client.put("/admin/roles/admin", headers=admin, json={"permissions": ["tickets:view"]}).status_code == 400
    assert client.put("/admin/roles/agent", headers=admin, json={"permissions": ["tickets:create"]}).status_code == 422
    assert client.put("/admin/roles/agent", headers=h(client, "a-agent@t.example"),
                      json={"permissions": ["tickets:view"]}).status_code == 403
    invalidate_cache()


def test_teams_and_routing_rules(client):
    admin = h(client, "a-admin@t.example")
    assert client.post("/admin/teams", headers=admin, json={"name": "Warranty Desk", "name_ar": "مكتب الضمان"}).status_code == 201
    assert client.post("/admin/teams", headers=admin, json={"name": "Warranty Desk"}).status_code == 409

    # route technical tickets to the new team
    routing = get_runtime(force=True)["team_routing"]
    routing = {**routing, "categories": {**routing["categories"], "technical": "Warranty Desk"}}
    assert client.patch("/settings", headers=admin, json={"values": {"team_routing": routing}}).status_code == 200
    get_runtime(force=True)
    tri = TriageResult(category=Category.technical, priority=Priority.P3, sentiment=Sentiment.neutral, sentiment_score=0)
    assert assign_team(tri, []) == "Warranty Desk"

    # can't deactivate a team that routing still uses; unknown teams rejected
    assert client.patch("/admin/teams/Warranty Desk", headers=admin, json={"is_active": False}).status_code == 409
    bad = {**routing, "categories": {**routing["categories"], "technical": "Nope"}}
    assert client.patch("/settings", headers=admin, json={"values": {"team_routing": bad}}).status_code == 422

    routing["categories"]["technical"] = "Technical Support"
    client.patch("/settings", headers=admin, json={"values": {"team_routing": routing}})
    get_runtime(force=True)
    assert client.patch("/admin/teams/Warranty Desk", headers=admin, json={"is_active": False}).status_code == 200
