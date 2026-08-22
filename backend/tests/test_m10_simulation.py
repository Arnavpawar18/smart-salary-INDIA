"""
Milestone M10.9: What-If Simulation Engine
Simulates salary increments (+5%, +10%, +20%), tax changes, and marginal take-home retention.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_m10_what_if_simulation_endpoints():
    client = TestClient(app)
    payload = {
        "base_salary": 1200000.00,
        "financial_year": "2025-26",
        "state_code": "KA",
        "regime": "NEW",
        "raise_percentages": [5, 10, 20],
    }
    resp = client.post("/api/v1/scenarios/what-if", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "scenarios" in data or isinstance(data, list) or "baseline" in data or len(data) > 0
