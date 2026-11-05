"""FastAPI dependencies: current user, permission checks, team scoping, audit."""
from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.auth.permissions import Permission, has_permission
from app.db.session import get_session
from app.models import db

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

UNAUTHORIZED = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated",
                             headers={"WWW-Authenticate": "Bearer"})


def current_user(token: str | None = Depends(oauth2), session: Session = Depends(get_session)) -> db.User:
    if not token:
        raise UNAUTHORIZED
    try:
        payload = jwt_payload(token)
    except jwt.PyJWTError:
        raise UNAUTHORIZED
    user = session.get(db.User, int(payload["sub"]))
    if user is None or not user.is_active:  # deactivation takes effect within one token lifetime
        raise UNAUTHORIZED
    return user


def jwt_payload(token: str) -> dict:
    from app.auth.security import decode_access_token
    return decode_access_token(token)


def require(*perms: Permission) -> Callable[..., db.User]:
    """Endpoint guard: `user = Depends(require(Permission.TICKETS_REVIEW))`."""
    def guard(user: db.User = Depends(current_user)) -> db.User:
        missing = [p.value for p in perms if not has_permission(user.role, p)]
        if missing:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Missing permission: {', '.join(missing)}")
        return user
    return guard


def can_see_ticket(user: db.User, ticket: db.Ticket) -> bool:
    """Team scoping. Users without VIEW_ALL see their team's tickets and ones assigned to them."""
    if has_permission(user.role, Permission.TICKETS_VIEW_ALL):
        return True
    return ticket.team == user.team or ticket.assignee_id == user.id


def client_ip(request: Request | None) -> str | None:
    """The real client IP. X-Forwarded-For is honored ONLY when the direct peer is a trusted
    proxy (the Next.js server); otherwise any client could spoof it to dodge rate limits.
    The right-most entry is the one appended by our proxy, so that's the one we trust."""
    if request is None or request.client is None:
        return None
    peer = request.client.host
    from app.config import get_settings
    trusted = {p.strip() for p in get_settings().trusted_proxies.split(",") if p.strip()}
    xff = request.headers.get("x-forwarded-for")
    if peer in trusted and xff:
        return xff.split(",")[-1].strip() or peer
    return peer


def audit(session: Session, user: db.User | None, action: str, target_type: str | None = None,
          target_id: str | None = None, request: Request | None = None, **detail) -> None:
    """Add an audit row to the caller's transaction (committed with the action itself)."""
    session.add(db.AuditLog(user_id=user.id if user else None, action=action, target_type=target_type,
                            target_id=target_id, detail=detail, ip=client_ip(request)))
