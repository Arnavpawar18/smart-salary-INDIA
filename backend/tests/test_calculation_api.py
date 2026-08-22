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
    # The calculation endpoint now requires authentication. An anonymous request should be rejected.
    assert response.status_code == 401
    # Optionally verify the error detail contains an authentication message.
    assert "Authentication required" in response.text


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


def test_htmx_calculator_post_anonymous_renders_auth_required_gate():
    form_data = {
        "financial_year": "2025-26",
        "regime": "NEW",
        "state_code": "KA",
        "annual_gross_salary": "1200000",
        "is_quick_mode": "true",
    }
    response = client.post("/calculator/calculate", data=form_data)
    assert response.status_code == 200
    assert "Authentication Required" in response.text
    assert "Create an account or sign in" in response.text
    assert "Sign In to Account" in response.text
    assert "Annual ₹1200000" in response.text
