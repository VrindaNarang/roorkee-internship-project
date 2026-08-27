from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_protected_endpoint_rejects_unauthenticated_requests() -> None:
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 401


def test_dashboard_summary(auth_headers: dict) -> None:
    response = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    assert "total_revenue" in response.json()


def test_recommendations_endpoints_respond(auth_headers: dict) -> None:
    for path in (
        "/api/v1/recommendations",
        "/api/v1/recommendations/customers",
        "/api/v1/recommendations/regions",
        "/api/v1/recommendations/high-priority",
        "/api/v1/recommendations/risk",
    ):
        response = client.get(path, headers=auth_headers)
        assert response.status_code == 200, path
        assert isinstance(response.json(), list)
