"""Create demo users, one per role (idempotent).

    python -m scripts.seed_users

DEV ONLY: all demo accounts share DEMO_PASSWORD (env var). Never run this against
a real deployment.
"""
import os

from sqlmodel import Session, select

from app.auth.permissions import seed_teams
from app.auth.security import hash_password
from app.db.session import engine, init_db
from app.models import db

PASSWORD = os.getenv("DEMO_PASSWORD", "Lumora-demo-2026")

DEMO_USERS = [
    ("admin@lumora.example", "Admin User", "admin", None, "en"),
    ("lead.tech@lumora.example", "Hala Nasser (Tech Lead)", "lead", "Technical Support", "ar"),
    ("agent.tech@lumora.example", "Karim Haddad (Tech Agent)", "agent", "Technical Support", "ar"),
    ("agent.refunds@lumora.example", "Emma Rossi (Refunds Agent)", "agent", "Returns & Refunds", "en"),
    ("agent.logistics@lumora.example", "Yusuf Darwish (Logistics Agent)", "agent", "Logistics", "ar"),
    ("lead.safety@lumora.example", "Leila Mansour (Safety Lead)", "lead", "Product Safety", "en"),
    ("analyst@lumora.example", "Noah Kim (Analyst)", "analyst", None, "en"),
]


def main() -> None:
    init_db()
    seed_teams()
    with Session(engine) as s:
        for email, name, role, team, lang in DEMO_USERS:
            if s.exec(select(db.User).where(db.User.email == email)).first():
                continue
            s.add(db.User(email=email, full_name=name, password_hash=hash_password(PASSWORD),
                          role=role, team=team, preferred_language=lang))
            print(f"created {role:<8} {email:<34} team={team}")
        s.commit()
    print(f"\nDemo password for all accounts: {PASSWORD}")


if __name__ == "__main__":
    main()
