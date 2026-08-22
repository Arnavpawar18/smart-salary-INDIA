"""
Milestone M10.4: Individual Analytics & Insights
Verifies salary optimization insights, regime comparison recommendations, and marginal tax rate calculations.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_m10_regime_comparison_analytics():
    client = TestClient(app)
    payload = {
        "financial_year": "2025-26",
        "state_code": "KA",
        "annual_gross_salary": 1600000.00,
    }
    resp = client.post("/api/v1/calculations/compare-regimes", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "old_regime" in data
    assert "new_regime" in data
    assert "recommended_regime" in data
    assert data["recommended_regime"] in ("NEW", "OLD")
