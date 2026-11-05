"""Administration: role permissions and teams. Requires USERS_MANAGE."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlmodel import Session, func, select

from app.auth.deps import audit, require
from app.auth.permissions import DEFAULT_ROLE_PERMISSIONS, Permission, Role, invalidate_cache, permissions_for
from app.db.session import get_session
from app.models import db

router = APIRouter(prefix="/admin", tags=["admin"])
ADMIN = require(Permission.USERS_MANAGE)


# ------------------------------------------------------------------ roles
@router.get("/roles")
def list_roles(_: db.User = Depends(ADMIN), session: Session = Depends(get_session)):
    counts = dict(session.exec(select(db.User.role, func.count()).where(db.User.is_active).group_by(db.User.role)).all())
    return [{"role": r.value, "permissions": permissions_for(r), "defaults": sorted(p.value for p in DEFAULT_ROLE_PERMISSIONS[r]),
             "editable": r != Role.admin, "users": counts.get(r.value, 0)} for r in Role]


class RoleIn(BaseModel):
    permissions: list[Permission]


@router.put("/roles/{role}")
def update_role(role: Role, body: RoleIn, request: Request, user: db.User = Depends(ADMIN),
                session: Session = Depends(get_session)):
    if role == Role.admin:
        raise HTTPException(400, "The admin role always has every permission and can't be edited")
    perms = sorted({p.value for p in body.permissions})
    if Permission.TICKETS_VIEW.value not in perms:
        raise HTTPException(422, "Every role needs tickets:view")
    before = permissions_for(role)
    row = session.get(db.RolePermissions, role.value)
    if row is None:
        session.add(db.RolePermissions(role=role.value, permissions=perms, updated_by=user.id))
    else:
        row.permissions, row.updated_by, row.updated_at = perms, user.id, db._now()
    audit(session, user, "role.update", "role", role.value, request,
          added=sorted(set(perms) - set(before)), removed=sorted(set(before) - set(perms)))
    session.commit()
    invalidate_cache()
    return {"role": role.value, "permissions": permissions_for(role)}


@router.post("/roles/{role}/reset")
def reset_role(role: Role, request: Request, user: db.User = Depends(ADMIN), session: Session = Depends(get_session)):
    row = session.get(db.RolePermissions, role.value)
    if row:
        session.delete(row)
        audit(session, user, "role.reset", "role", role.value, request)
        session.commit()
    invalidate_cache()
    return {"role": role.value, "permissions": permissions_for(role)}


# ------------------------------------------------------------------ teams
class TeamIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    name_ar: str = Field(default="", max_length=60)
    description: str = Field(default="", max_length=300)


class TeamPatch(BaseModel):
    name_ar: str | None = Field(default=None, max_length=60)
    description: str | None = Field(default=None, max_length=300)
    is_active: bool | None = None


@router.get("/teams")
def list_teams(_: db.User = Depends(require(Permission.TICKETS_VIEW)), session: Session = Depends(get_session)):
    members = dict(session.exec(select(db.User.team, func.count()).where(db.User.is_active).group_by(db.User.team)).all())
    open_tickets = dict(session.exec(select(db.Ticket.team, func.count())
                                     .where(db.Ticket.status.in_(["in_review", "escalated", "ready_to_send", "new"]))
                                     .group_by(db.Ticket.team)).all())
    return [{**t.model_dump(mode="json"), "members": members.get(t.name, 0), "open_tickets": open_tickets.get(t.name, 0)}
            for t in session.exec(select(db.TeamRow).order_by(db.TeamRow.name)).all()]


@router.post("/teams", status_code=201)
def create_team(body: TeamIn, request: Request, user: db.User = Depends(ADMIN), session: Session = Depends(get_session)):
    name = body.name.strip()
    if session.get(db.TeamRow, name):
        raise HTTPException(409, "A team with this name already exists")
    session.add(db.TeamRow(name=name, name_ar=body.name_ar.strip(), description=body.description.strip()))
    audit(session, user, "team.create", "team", name, request)
    session.commit()
    return session.get(db.TeamRow, name).model_dump(mode="json")


@router.patch("/teams/{name}")
def update_team(name: str, body: TeamPatch, request: Request, user: db.User = Depends(ADMIN),
                session: Session = Depends(get_session)):
    team = session.get(db.TeamRow, name)
    if team is None:
        raise HTTPException(404, "Team not found")
    if body.is_active is False:
        from app.runtime_settings import get_runtime
        routing = get_runtime(force=True)["team_routing"]
        used_by = [f"{sec}.{k}" for sec, m in routing.items() for k, v in m.items() if v == name]
        if used_by:
            raise HTTPException(409, f"Team is used by routing rules ({', '.join(used_by)}). Re-route them first.")
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(team, k, v)
    audit(session, user, "team.update", "team", name, request, changes=changes)
    session.commit()
    return team.model_dump(mode="json")
