from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_api_contract():
    """Verify response structure and types of /api/v1/health."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded"]
    assert "database" in data
    assert data["database"] in ["connected", "unreachable"]
    assert "timestamp" in data
