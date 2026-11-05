from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlmodel import Session, func, select

from app.auth.deps import audit, client_ip, current_user
from app.config import get_settings
from app.auth.permissions import permissions_for
from app.auth.security import create_access_token, hash_token, new_refresh_token, verify_password
from app.db.session import get_session
from app.models import db

router = APIRouter(prefix="/auth", tags=["auth"])
REUSE_GRACE_S = 30


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshIn(BaseModel):
    refresh_token: str


def _issue(session: Session, user: db.User) -> TokenPair:
    access, ttl = create_access_token(user.id, user.role)
    refresh, refresh_hash, expires = new_refresh_token()
    session.add(db.RefreshToken(user_id=user.id, token_hash=refresh_hash, expires_at=expires))
    return TokenPair(access_token=access, refresh_token=refresh, expires_in=ttl)


def user_out(u: db.User) -> dict:
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role, "team": u.team,
            "preferred_language": u.preferred_language, "is_active": u.is_active,
            "permissions": permissions_for(u.role),
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None}


def _check_login_rate(session: Session, email: str, ip: str | None) -> None:
    """Brute-force protection, counted from the audit log (works across processes, no Redis).
    Three limits: account+IP (normal guessing), account from any IP (distributed attack),
    and IP across accounts (password spraying). Checked BEFORE the password is verified."""
    s = get_settings()
    since = datetime.now(timezone.utc) - timedelta(minutes=s.login_window_minutes)
    base = select(func.count()).select_from(db.AuditLog).where(
        db.AuditLog.action == "auth.login_failed", db.AuditLog.created_at >= since)
    checks = [(base.where(db.AuditLog.target_id == email), s.login_max_per_account)]
    if ip:
        checks += [(base.where(db.AuditLog.target_id == email, db.AuditLog.ip == ip), s.login_max_per_account_ip),
                   (base.where(db.AuditLog.ip == ip), s.login_max_per_ip)]
    for query, limit in checks:
        if session.exec(query).one() >= limit:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                                f"Too many failed sign-in attempts. Try again in {s.login_window_minutes} minutes.",
                                headers={"Retry-After": str(s.login_window_minutes * 60)})


@router.post("/login", response_model=TokenPair)
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    """OAuth2 password flow (form fields: username = email, password)."""
    email = form.username.lower().strip()
    ip = client_ip(request)
    _check_login_rate(session, email, ip)
    user = session.exec(select(db.User).where(db.User.email == email)).first()
    # Same error for "no such user" and "wrong password": don't reveal which emails exist.
    if user is None or not user.is_active or not verify_password(form.password, user.password_hash):
        audit(session, user, "auth.login_failed", "user", email, request)
        session.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    user.last_login_at = datetime.now(timezone.utc)
    pair = _issue(session, user)
    audit(session, user, "auth.login", "user", str(user.id), request)
    session.commit()
    return pair


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshIn, request: Request, session: Session = Depends(get_session)):
    row = session.exec(select(db.RefreshToken).where(db.RefreshToken.token_hash == hash_token(body.refresh_token))).first()
    now = datetime.now(timezone.utc)
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    if row.revoked_at is not None:
        revoked = row.revoked_at if row.revoked_at.tzinfo else row.revoked_at.replace(tzinfo=timezone.utc)
        if (now - revoked).total_seconds() < REUSE_GRACE_S:
            # Two tabs refreshing at the same moment: a race, not theft. Just reject this one.
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token already rotated")
        # Reuse of a rotated token long after rotation = likely theft. Kill every session of this user.
        for t in session.exec(select(db.RefreshToken).where(db.RefreshToken.user_id == row.user_id,
                                                             db.RefreshToken.revoked_at.is_(None))):
            t.revoked_at = now
        audit(session, session.get(db.User, row.user_id), "auth.refresh_reuse_detected", "user", str(row.user_id), request)
        session.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token reuse detected; all sessions revoked")
    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    user = session.get(db.User, row.user_id)
    if expires < now or user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token expired")
    row.revoked_at = now  # rotation: each refresh token works exactly once
    pair = _issue(session, user)
    session.commit()
    return pair


@router.post("/logout", status_code=204)
def logout(body: RefreshIn, request: Request, session: Session = Depends(get_session)):
    row = session.exec(select(db.RefreshToken).where(db.RefreshToken.token_hash == hash_token(body.refresh_token))).first()
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        audit(session, session.get(db.User, row.user_id), "auth.logout", "user", str(row.user_id), request)
        session.commit()


@router.get("/me")
def me(user: db.User = Depends(current_user)):
    return user_out(user)


class PrefsIn(BaseModel):
    preferred_language: str


@router.patch("/me")
def update_me(body: PrefsIn, user: db.User = Depends(current_user), session: Session = Depends(get_session)):
    if body.preferred_language not in ("en", "ar"):
        raise HTTPException(422, "preferred_language must be 'en' or 'ar'")
    user = session.merge(user)
    user.preferred_language = body.preferred_language
    session.commit()
    session.refresh(user)
    return user_out(user)
