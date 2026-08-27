"""Shared pytest fixtures — primarily authenticated-client headers, since
every endpoint except `/auth/login` now requires a bearer token (Milestone
11). Tests ensure their own test users exist (idempotently) rather than
depending on `app/db/seed_users.py` having been run first, so the suite is
self-contained.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models import User

TEST_PASSWORD = "test-password-123"

client = TestClient(app)


def _ensure_user(email: str, role: str) -> None:
    db = SessionLocal()
    try:
        existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing is None:
            db.add(
                User(
                    email=email,
                    full_name=f"Test {role.replace('_', ' ').title()}",
                    role=role,
                    hashed_password=hash_password(TEST_PASSWORD),
                    is_active=True,
                )
            )
            db.commit()
    finally:
        db.close()


def _login_headers(email: str, role: str) -> dict:
    _ensure_user(email, role)
    response = client.post("/api/v1/auth/login", data={"username": email, "password": TEST_PASSWORD})
    response.raise_for_status()
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def auth_headers() -> dict:
    """The default "just log me in" fixture — an admin user, since admin can
    reach every endpoint including the role-restricted ones."""
    return _login_headers("test-admin@salespilot.example.com", "admin")


@pytest.fixture(scope="session")
def sales_manager_headers() -> dict:
    return _login_headers("test-manager@salespilot.example.com", "sales_manager")


@pytest.fixture(scope="session")
def sales_executive_headers() -> dict:
    return _login_headers("test-executive@salespilot.example.com", "sales_executive")
