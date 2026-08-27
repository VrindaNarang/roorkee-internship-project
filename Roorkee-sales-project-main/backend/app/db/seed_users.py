"""Seeds three demo accounts, one per role, so the app is usable immediately
after a fresh `alembic upgrade head` without a separate user-registration
flow (none exists — see PROJECT_SPEC.md Milestone 11: this is internal
software with a fixed, small user base, not self-service signup).

Kept separate from `seed.py` (sales mock data) on purpose: user accounts and
sales data have unrelated lifecycles — resetting/re-generating mock orders
should never also wipe out logins.

Run with:
    cd backend
    .venv/Scripts/python.exe -m app.db.seed_users

DEMO CREDENTIALS (change before any real deployment — see README "Security
Notes"): all three accounts use the password `ChangeMe123!`.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.db.session import SessionLocal
from app.models import User

DEMO_PASSWORD = "ChangeMe123!"

DEMO_USERS = [
    {"email": "admin@salespilot.example.com", "full_name": "Admin User", "role": "admin"},
    {"email": "manager@salespilot.example.com", "full_name": "Sales Manager", "role": "sales_manager"},
    {"email": "executive@salespilot.example.com", "full_name": "Sales Executive", "role": "sales_executive"},
]


def seed_default_users(db: Session) -> list[User]:
    created: list[User] = []
    for spec in DEMO_USERS:
        existing = db.execute(select(User).where(User.email == spec["email"])).scalar_one_or_none()
        if existing is not None:
            continue
        user = User(
            email=spec["email"],
            full_name=spec["full_name"],
            role=spec["role"],
            hashed_password=hash_password(DEMO_PASSWORD),
            is_active=True,
        )
        db.add(user)
        created.append(user)
    db.commit()
    return created


def main() -> None:
    db = SessionLocal()
    try:
        created = seed_default_users(db)
        if not created:
            print("All demo users already exist — nothing to do.")
            return
        print(f"Created {len(created)} demo user(s):")
        for spec in DEMO_USERS:
            print(f"  {spec['role']:<16} {spec['email']}  (password: {DEMO_PASSWORD})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
