import uuid
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.security import JWTProvider
from app.main import app
from app.models.auth import User
from app.models.employee import Employee


def _get_authenticated_client(db_session):
    client = TestClient(app)
    test_user = User(
        email=f"m10_inputs_{uuid.uuid4().hex[:6]}@smartsalary.in",
        hashed_password="mock_hashed_password_2026",
        full_name="M10 Inputs User",
        is_active=True,
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    emp = Employee(
        user_id=test_user.id,
        first_name="M10",
        last_name="Inputs",
        email=test_user.email,
        date_of_joining=date(2025, 4, 1),
        employee_code=f"EMP-INP-{uuid.uuid4().hex[:4]}",
    )
    db_session.add(emp)
    db_session.commit()
    db_session.refresh(emp)

    token = JWTProvider.create_access_token(user_id=test_user.id, role="EMPLOYEE", employee_id=emp.id)
    client.cookies.set("access_token", token)
    return client


def test_m10_salary_negative_input_rejected(db_session):
    client = _get_authenticated_client(db_session)
    payload = {
        "financial_year": "2025-26",
        "annual_gross_salary": -50000.00,
        "state_code": "KA",
        "regime": "NEW",
    }
    resp = client.post("/api/v1/calculations", json=payload)
    assert resp.status_code in (400, 422)


def test_m10_salary_decimal_precision_preservation(db_session):
    client = _get_authenticated_client(db_session)
    # Gross with cents
    payload = {
        "financial_year": "2025-26",
        "annual_gross_salary": 1250000.50,
        "state_code": "KA",
        "regime": "NEW",
    }
    resp = client.post("/api/v1/calculations", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert Decimal(str(data["annual_gross_salary"])) == Decimal("1250000.50")

