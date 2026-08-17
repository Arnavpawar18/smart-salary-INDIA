from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_metadata_api_contract():
    """Verify response structure and 40-table count of /api/v1/metadata/schema-summary."""
    response = client.get("/api/v1/metadata/schema-summary")
    assert response.status_code == 200

    data = response.json()
    assert "total_domain_tables" in data
    assert data["total_domain_tables"] == 40
    assert "domains" in data
    assert "migration_revision" in data
    assert data["migration_revision"] == "001_initial_domain_schema"
    assert "financial_years" in data
    assert data["financial_years"] == ["2024-25", "2025-26", "2026-27"]

    # Verify that the sum of tables in domains equals 40
    total_in_domains = sum(len(tables) for tables in data["domains"].values())
    assert total_in_domains == 40
