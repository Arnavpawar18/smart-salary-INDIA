from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_calculations_api_endpoint():
    payload = {
        "financial_year": "2025-26",
        "regime": "NEW",
        "state_code": "KA",
        "annual_gross_salary": 1200000.0,
    }
    response = client.post("/api/v1/calculations", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["financial_year"] == "2025-26"
    assert data["regime"] == "NEW"
    assert data["state_code"] == "KA"
    assert data["total_annual_tax_liability"] == "0.00"  # u/s 87A rebate
    assert len(data["line_items"]) > 0
    assert len(data["trace_steps"]) > 0
    assert len(data["result_hash"]) == 64


def test_compare_regimes_api_endpoint():
    payload = {
        "financial_year": "2025-26",
        "state_code": "KA",
        "annual_gross_salary": 1500000.0,
    }
    response = client.post("/api/v1/calculations/compare-regimes", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "old_regime" in data
    assert "new_regime" in data
    assert "recommended_regime" in data


def test_htmx_calculator_post_renders_partial():
    form_data = {
        "financial_year": "2025-26",
        "regime": "NEW",
        "state_code": "KA",
        "annual_gross_salary": "1200000",
    }
    response = client.post("/calculator/calculate", data=form_data)
    assert response.status_code == 200
    assert "Estimated Take-Home & Tax Liability" in response.text
    assert "Standard Deduction u/s 16(ia)" in response.text
