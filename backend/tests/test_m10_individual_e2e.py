import uuid
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.security import JWTProvider
from app.main import app
from app.models.auth import User
from app.models.employee import Employee


def test_m10_individual_complete_journey(db_session):
    client = TestClient(app)

    # 1. Fetch metadata & system context
    meta_resp = client.get("/api/v1/ui/context")
    assert meta_resp.status_code == 200
    meta_data = meta_resp.json()
    assert "tax_periods" in meta_data or "states" in meta_data

    # 2. Authenticate test user
    test_user = User(
        email=f"m10_journey_{uuid.uuid4().hex[:6]}@smartsalary.in",
        hashed_password="mock_hashed_password_2026",
        full_name="M10 Journey User",
        is_active=True,
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    emp = Employee(
        user_id=test_user.id,
        first_name="M10",
        last_name="Journey",
        email=test_user.email,
        date_of_joining=date(2025, 4, 1),
        employee_code=f"EMP-JNY-{uuid.uuid4().hex[:4]}",
    )
    db_session.add(emp)
    db_session.commit()
    db_session.refresh(emp)

    token = JWTProvider.create_access_token(user_id=test_user.id, role="EMPLOYEE", employee_id=emp.id)
    client.cookies.set("access_token", token)

    # 3. Execute deterministic calculation for Bangalore resident
    calc_payload = {
        "financial_year": "2025-26",
        "annual_gross_salary": 1500000.00,
        "state_code": "KA",
        "regime": "NEW",
    }
    calc_resp = client.post("/api/v1/calculations", json=calc_payload)
    assert calc_resp.status_code == 201
    calc_res = calc_resp.json()

    # 4. Assert exact 3-view mathematical consistency (Gross -> Deductions -> Take-Home)
    annual_gross = Decimal(str(calc_res["annual_gross_salary"]))
    total_tax = Decimal(str(calc_res["total_annual_tax_liability"]))
    annual_pf = Decimal(str(calc_res["annual_employee_pf"]))
    annual_pt = Decimal(str(calc_res["annual_professional_tax"]))
    take_home = Decimal(str(calc_res["estimated_annual_take_home"]))

    assert annual_gross == Decimal("1500000.00")
    assert total_tax + annual_pf + annual_pt + take_home == annual_gross
    assert len(calc_res["line_items"]) > 0
    assert len(calc_res["trace_steps"]) > 0
    assert len(calc_res["result_hash"]) == 64

