from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Session, select

from app.auth.deps import audit, require
from app.auth.permissions import Permission, Role, permissions_for, team_names
from app.auth.router import user_out
from app.auth.security import hash_password
from app.db.session import get_session
from app.models import db

router = APIRouter(prefix="/users", tags=["users"])
ADMIN = require(Permission.USERS_MANAGE)


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=10, max_length=128)
    role: Role
    team: str | None = None
    preferred_language: str = "en"


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: Role | None = None
    team: str | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=10, max_length=128)


def _validate_team(role: Role | str, team: str | None) -> None:
    if team is not None and team not in team_names():
        raise HTTPException(422, f"Unknown team '{team}'")
    if Role(role) in (Role.agent, Role.lead) and not team:
        raise HTTPException(422, "Agents and team leads must belong to a team")


@router.get("/meta")
def meta(_: db.User = Depends(require(Permission.TICKETS_VIEW))):
    """Roles, their permissions, and teams (for UI dropdowns and the permissions matrix)."""
    return {"roles": {r.value: permissions_for(r) for r in Role}, "teams": team_names(),
            "all_permissions": [p.value for p in Permission]}


@router.get("/assignable")
def assignable(_: db.User = Depends(require(Permission.TICKETS_REASSIGN)), session: Session = Depends(get_session)):
    """Minimal view (no emails/permissions) so leads can assign tickets without USERS_MANAGE."""
    rows = session.exec(select(db.User).where(db.User.is_active, db.User.role.in_(["agent", "lead"]))
                        .order_by(db.User.team, db.User.full_name)).all()
    return [{"id": u.id, "full_name": u.full_name, "team": u.team, "role": u.role} for u in rows]


@router.get("")
def list_users(_: db.User = Depends(ADMIN), session: Session = Depends(get_session)):
    return [user_out(u) for u in session.exec(select(db.User).order_by(db.User.id)).all()]


@router.post("", status_code=201)
def create_user(body: UserCreate, request: Request, admin: db.User = Depends(ADMIN),
                session: Session = Depends(get_session)):
    _validate_team(body.role, body.team)
    email = body.email.lower()
    if session.exec(select(db.User).where(db.User.email == email)).first():
        raise HTTPException(409, "A user with this email already exists")
    user = db.User(email=email, full_name=body.full_name, password_hash=hash_password(body.password),
                   role=body.role.value, team=body.team, preferred_language=body.preferred_language)
    session.add(user)
    session.flush()
    audit(session, admin, "user.create", "user", str(user.id), request, role=user.role, team=user.team)
    session.commit()
    session.refresh(user)
    return user_out(user)


@router.patch("/{user_id}")
def update_user(user_id: int, body: UserUpdate, request: Request, admin: db.User = Depends(ADMIN),
                session: Session = Depends(get_session)):
    user = session.get(db.User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    if user.id == admin.id and (body.is_active is False or (body.role and body.role != Role.admin)):
        raise HTTPException(400, "You can't deactivate or demote yourself")  # avoid locking out the last admin

    changes = body.model_dump(exclude_unset=True, exclude={"password"})
    new_role = body.role or Role(user.role)
    _validate_team(new_role, changes.get("team", user.team))
    for k, v in changes.items():
        setattr(user, k, v.value if isinstance(v, Role) else v)
    if body.password:
        user.password_hash = hash_password(body.password)
        changes["password"] = "changed"
    if body.is_active is False:  # deactivation also revokes all sessions
        for t in session.exec(select(db.RefreshToken).where(db.RefreshToken.user_id == user.id,
                                                             db.RefreshToken.revoked_at.is_(None))):
            t.revoked_at = db._now()
    audit(session, admin, "user.update", "user", str(user.id), request,
          changes={k: (v.value if isinstance(v, Role) else v) for k, v in changes.items()})
    session.commit()
    session.refresh(user)
    return user_out(user)


@router.get("/audit")
def audit_log(limit: int = 200, _: db.User = Depends(require(Permission.AUDIT_VIEW)),
              session: Session = Depends(get_session)):
    rows = session.exec(select(db.AuditLog).order_by(db.AuditLog.id.desc()).limit(min(limit, 1000))).all()
    return [r.model_dump(mode="json") for r in rows]
