"""Authentication & RBAC tests (Milestone 11)."""

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_PASSWORD, _ensure_user

client = TestClient(app)


def test_login_succeeds_with_correct_credentials(auth_headers: dict) -> None:
    # auth_headers fixture already proved login works; this test asserts the
    # shape of a fresh login response directly.
    _ensure_user("test-login-shape@salespilot.example.com", "admin")
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test-login-shape@salespilot.example.com", "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "admin"
    assert body["access_token"]


def test_login_fails_with_wrong_password() -> None:
    _ensure_user("test-wrong-password@salespilot.example.com", "admin")
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test-wrong-password@salespilot.example.com", "password": "not-the-real-password"},
    )
    assert response.status_code == 401


def test_login_fails_for_unknown_email() -> None:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "nobody-with-this-email@salespilot.example.com", "password": "irrelevant"},
    )
    assert response.status_code == 401


def test_me_returns_the_authenticated_users_profile(auth_headers: dict) -> None:
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "test-admin@salespilot.example.com"
    assert body["role"] == "admin"


def test_me_rejects_missing_token() -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_rejects_malformed_token() -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert response.status_code == 401


def test_protected_endpoint_accepts_any_authenticated_role(
    auth_headers: dict, sales_manager_headers: dict, sales_executive_headers: dict
) -> None:
    for headers in (auth_headers, sales_manager_headers, sales_executive_headers):
        response = client.get("/api/v1/dashboard/summary", headers=headers)
        assert response.status_code == 200


def test_retrain_endpoint_allows_admin_and_sales_manager(
    monkeypatch, auth_headers: dict, sales_manager_headers: dict
) -> None:
    """Confirms the *role check* passes for these two roles — the actual ML
    subprocess is stubbed out (it shells out to a whole separate pipeline
    that takes ~a minute; a unit test should not run it for real, and
    definitely not twice).
    """
    import subprocess
    from pathlib import Path

    from app.api.v1.routers import ml_admin

    fake_result = subprocess.CompletedProcess(args=[], returncode=0, stdout='{"version": "stub"}', stderr="")
    monkeypatch.setattr(ml_admin.subprocess, "run", lambda *a, **k: fake_result)
    monkeypatch.setattr(ml_admin, "ML_PYTHON", Path(__file__))  # any real file — only `.exists()` is checked

    for headers in (auth_headers, sales_manager_headers):
        response = client.post("/api/v1/ml/retrain", headers=headers)
        assert response.status_code != 403


def test_retrain_endpoint_forbids_sales_executive(sales_executive_headers: dict) -> None:
    response = client.post("/api/v1/ml/retrain", headers=sales_executive_headers)
    assert response.status_code == 403


def test_recalculate_health_forbids_sales_executive(sales_executive_headers: dict) -> None:
    response = client.post("/api/v1/customers/health", headers=sales_executive_headers)
    assert response.status_code == 403


def test_inactive_user_cannot_log_in() -> None:
    from sqlalchemy import select

    from app.auth.security import hash_password
    from app.db.session import SessionLocal
    from app.models import User

    email = "test-inactive@salespilot.example.com"
    db = SessionLocal()
    try:
        if db.execute(select(User).where(User.email == email)).scalar_one_or_none() is None:
            db.add(
                User(
                    email=email,
                    full_name="Inactive User",
                    role="sales_executive",
                    hashed_password=hash_password(TEST_PASSWORD),
                    is_active=False,
                )
            )
            db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test-inactive@salespilot.example.com", "password": TEST_PASSWORD},
    )
    assert response.status_code == 401
