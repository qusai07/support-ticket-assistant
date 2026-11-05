"""Password hashing (Argon2) and tokens.

- Access token: short-lived JWT (15 min), stateless, carries user id + role.
- Refresh token: random opaque string (not a JWT), stored as SHA-256 in the DB,
  rotated on every use. Reusing an already-rotated token revokes all of that
  user's sessions (a sign the token was stolen).
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.config import get_settings

_hasher = PasswordHash.recommended()  # Argon2id
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password, password_hash)
    except Exception:
        return False


def create_access_token(user_id: int, role: str) -> tuple[str, int]:
    s = get_settings()
    now = datetime.now(timezone.utc)
    ttl = s.access_token_minutes * 60
    payload = {"sub": str(user_id), "role": role, "type": "access", "iat": now,
               "exp": now + timedelta(seconds=ttl), "jti": uuid.uuid4().hex}
    return jwt.encode(payload, s.jwt_secret, algorithm=ALGORITHM), ttl


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError on invalid/expired tokens."""
    payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("not an access token")
    return payload


def new_refresh_token() -> tuple[str, str, datetime]:
    """Returns (token to give the client, hash to store, expiry)."""
    token = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + timedelta(days=get_settings().refresh_token_days)
    return token, hash_token(token), expires


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
