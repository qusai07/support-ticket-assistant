"""Brute-force protection on /auth/login and trusted-proxy IP handling (no LLM)."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth.security import hash_password
from app.db.session import engine, init_db
from app.main import app
from app.models import db

PW = "correct-horse-battery"


@pytest.fixture(scope="module")
def client():
    init_db()
    with Session(engine) as s:
        for email in ("rl-victim@t.example", "rl-other@t.example", "rl-ok@t.example"):
            if not s.exec(select(db.User).where(db.User.email == email)).first():
                s.add(db.User(email=email, full_name=email, password_hash=hash_password(PW), role="agent", team="Logistics"))
        s.commit()
    return TestClient(app)  # TestClient's peer is "testclient": not a trusted proxy


def attempt(client, email, password="wrong", ip=None):
    headers = {"X-Forwarded-For": ip} if ip else {}
    return client.post("/auth/login", data={"username": email, "password": password}, headers=headers)


def test_locks_after_five_failures_even_with_correct_password(client):
    for _ in range(5):
        assert attempt(client, "rl-victim@t.example").status_code == 401
    r = attempt(client, "rl-victim@t.example", PW)       # right password, but locked
    assert r.status_code == 429 and r.headers["Retry-After"] == "900"
    assert attempt(client, "rl-ok@t.example", PW).status_code == 200   # other accounts unaffected


def test_spoofed_forwarded_for_is_ignored_from_untrusted_peer(client):
    # An attacker rotating X-Forwarded-For can't reset the per-account+IP counter,
    # because the header is only trusted from the Next.js proxy (127.0.0.1).
    for i in range(5):
        attempt(client, "rl-other@t.example", ip=f"10.0.0.{i}")
    assert attempt(client, "rl-other@t.example", PW, ip="10.9.9.9").status_code == 429
