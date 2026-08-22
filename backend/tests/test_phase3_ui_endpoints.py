import uuid
from datetime import date

from fastapi.testclient import TestClient

from app.core.security import JWTProvider
from app.main import app
from app.models.auth import User
from app.models.employee import Employee

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


def test_htmx_minimal_result_and_how_lazy_load_flow(db_session):
    # 1. Anonymous submission renders Level 1 Auth Required card
    anon_res = client.post(
        "/calculator/calculate",
        data={
            "financial_year": "2025-26",
            "regime": "NEW",
            "state_code": "KA",
            "monthly_gross_salary": "100000",
            "is_quick_mode": "true",
        },
    )
    assert anon_res.status_code == 200
    assert "Authentication Required" in anon_res.text
    assert "Sign In to Account" in anon_res.text

    # 2. Authenticate user
    test_user = User(
        email=f"phase3_ui_{uuid.uuid4().hex[:6]}@smartsalary.in",
        hashed_password="mock_hashed_password_2026",
        full_name="Phase 3 UI User",
        is_active=True,
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    emp = Employee(
        user_id=test_user.id,
        first_name="Phase3",
        last_name="User",
        email=test_user.email,
        date_of_joining=date(2025, 4, 1),
        employee_code=f"EMP-P3-{uuid.uuid4().hex[:4]}",
    )
    db_session.add(emp)
    db_session.commit()
    db_session.refresh(emp)

    token = JWTProvider.create_access_token(user_id=test_user.id, role="EMPLOYEE", employee_id=emp.id)
    auth_client = TestClient(app)
    auth_client.cookies.set("access_token", token)

    # 3. Authenticated submission returns minimal result and How CTA
    auth_res = auth_client.post(
        "/calculator/calculate",
        data={
            "financial_year": "2025-26",
            "regime": "NEW",
            "state_code": "KA",
            "monthly_gross_salary": "100000",
            "is_quick_mode": "true",
        },
    )
    assert auth_res.status_code == 200
    html = auth_res.text
    assert "Your Calculation Result" in html
    assert "Estimated Annual Take-Home" in html
    assert "HOW WAS THIS CALCULATED?" in html

    # 4. Extract calculation ID and lazy-load How details
    how_res = auth_client.get("/calculator/1/how")
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
