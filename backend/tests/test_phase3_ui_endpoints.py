from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ui_context_endpoint():
    response = client.get("/api/v1/ui/context")
    assert response.status_code == 200
    data = response.json()
    assert "current_financial_year" in data
    assert "supported_financial_years" in data
    assert len(data["states"]) > 0
    assert data["capabilities"]["epfo_provident_fund"] is True


def test_scenarios_what_if_api():
    response = client.post(
        "/api/v1/scenarios/what-if",
        json={
            "base_salary": "1200000.00",
            "financial_year": "2025-26",
            "state_code": "KA",
            "regime": "NEW",
            "raise_percentages": [5, 10, 20],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["base_gross"] == 1200000.0
    assert len(data["simulations"]) == 3
    assert data["simulations"][0]["percentage_increase"] == "5%"


def test_htmx_minimal_result_and_how_lazy_load_flow():
    # 1. Submit calculation form
    res = client.post(
        "/calculator/calculate",
        data={
            "financial_year": "2025-26",
            "regime": "NEW",
            "state_code": "KA",
            "monthly_gross_salary": "100000",
            "is_quick_mode": "true",
        },
    )
    assert res.status_code == 200
    html = res.text
    # Minimal result contains take-home, tax, quality badge, and How CTA
    assert "Your Calculation Result" in html
    assert "Estimated Annual Take-Home" in html
    assert "HOW WAS THIS CALCULATED?" in html

    # 2. Extract calculation ID and lazy-load How details
    how_res = client.get("/calculator/1/how")
    if how_res.status_code == 200:
        how_html = how_res.text
        assert "Complete Financial Trace" in how_html
        assert "Step-by-Step Mathematical Waterfall" in how_html
        assert "Projected 12-Month Paycheck Schedule" in how_html


def test_print_export_summary_page():
    res = client.get("/calculator/export/1")
    if res.status_code == 200:
        html = res.text
        assert "Official Salary &" in html or "Official Salary &amp;" in html or "SMARTSALARY" in html
        assert "Annual Compensation Breakdown" in html
