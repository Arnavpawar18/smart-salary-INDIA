import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.core.security import JWTProvider, PasswordHasher
from app.main import app
from app.models.auth import Role, User, user_roles
from app.models.employee import Employee
from app.services.calculation_save_service import CalculationSaveService

client = TestClient(app)


@pytest.fixture
def test_user_pair():
    """Creates two distinct employees for cross-user authorization tests."""
    with SessionLocal() as db:
        role_emp = db.scalar(select(Role).where(Role.name == "EMPLOYEE"))

        # User A
        email_a = f"user_a_{uuid.uuid4().hex[:8]}@smartsalary.in"
        user_a = User(email=email_a, hashed_password=PasswordHasher.hash_password("PassA123!"), full_name="User Alpha")
        db.add(user_a)
        db.flush()
        if role_emp:
            db.execute(user_roles.insert().values(user_id=user_a.id, role_id=role_emp.id))
        emp_a = Employee(
            user_id=user_a.id,
            employee_code=f"EMP-{user_a.id:04d}",
            first_name="Alpha",
            last_name="User",
            email=email_a,
            date_of_joining=date.today(),
            state_id=1,
        )
        db.add(emp_a)

        # User B
        email_b = f"user_b_{uuid.uuid4().hex[:8]}@smartsalary.in"
        user_b = User(email=email_b, hashed_password=PasswordHasher.hash_password("PassB123!"), full_name="User Beta")
        db.add(user_b)
        db.flush()
        if role_emp:
            db.execute(user_roles.insert().values(user_id=user_b.id, role_id=role_emp.id))
        emp_b = Employee(
            user_id=user_b.id,
            employee_code=f"EMP-{user_b.id:04d}",
            first_name="Beta",
            last_name="User",
            email=email_b,
            date_of_joining=date.today(),
            state_id=1,
        )
        db.add(emp_b)
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)
        db.refresh(emp_a)
        db.refresh(emp_b)

        # Create a saved calculation for User B
        calc_svc = CalculationSaveService(db)
        calc_b = calc_svc.save_calculation_for_employee(
            employee_id=emp_b.id,
            financial_year="2025-26",
            regime="NEW",
            annual_gross=Decimal("1500000.00"),
            taxable_income=Decimal("1425000.00"),
            total_tax=Decimal("150000.00"),
            take_home=Decimal("1350000.00"),
            result_snapshot={"annual_gross": "1500000.00"},
            trace_events=[],
        )

        u_a_id = user_a.id
        u_a_email = user_a.email
        e_a_id = emp_a.id

        u_b_id = user_b.id
        u_b_email = user_b.email
        e_b_id = emp_b.id
        c_b_id = calc_b.id

        return {
            "user_a_id": u_a_id,
            "user_a_email": u_a_email,
            "emp_a_id": e_a_id,
            "user_b_id": u_b_id,
            "user_b_email": u_b_email,
            "emp_b_id": e_b_id,
            "calc_b_id": c_b_id,
        }


from sqlalchemy import select


def test_idor_cross_user_calculation_denial(test_user_pair):
    """
    IDOR Test: User A attempts to read User B's calculation record.
    Must receive 404 (or 403) and must NOT leak User B's financial data.
    """
    user_a_id = test_user_pair["user_a_id"]
    emp_a_id = test_user_pair["emp_a_id"]
    calc_b_id = test_user_pair["calc_b_id"]

    token_a = JWTProvider.create_access_token(user_id=user_a_id, role="EMPLOYEE", employee_id=emp_a_id)

    # User A requests User B's calculation
    res = client.get(f"/api/v1/calculations/{calc_b_id}", cookies={"access_token": token_a})
    assert res.status_code == 404
    assert "not found or unauthorized" in res.json()["detail"].lower()


def test_unauthenticated_access_denial(test_user_pair):
    """
    Unauthenticated request to /dashboard or /calculations/history must return 401.
    """
    res_dash = client.get("/dashboard")
    assert res_dash.status_code == 401

    res_hist = client.get("/api/v1/calculations/history")
    assert res_hist.status_code == 401


def test_authenticated_dashboard_renders_own_data(test_user_pair):
    """
    User A requests /dashboard and receives their own profile and records.
    """
    user_a_id = test_user_pair["user_a_id"]
    emp_a_id = test_user_pair["emp_a_id"]
    token_a = JWTProvider.create_access_token(user_id=user_a_id, role="EMPLOYEE", employee_id=emp_a_id)

    res = client.get("/dashboard", cookies={"access_token": token_a})
    assert res.status_code == 200
    assert "Good day, Alpha" in res.text
    assert "Multi-Year Financial Trend" in res.text


def test_session_security_and_password_change(test_user_pair):
    """
    Tests Password Change and Session Revocation lifecycle.
    """
    user_a_id = test_user_pair["user_a_id"]
    user_a_email = test_user_pair["user_a_email"]
    emp_a_id = test_user_pair["emp_a_id"]
    token_a = JWTProvider.create_access_token(user_id=user_a_id, role="EMPLOYEE", employee_id=emp_a_id)

    # 1. Change password successfully
    res_chg = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "PassA123!",
            "new_password": "NewStrongPass2026!",
            "confirm_password": "NewStrongPass2026!",
        },
        cookies={"access_token": token_a},
    )
    assert res_chg.status_code == 200

    # 2. Login with old password must fail
    res_old = client.post(
        "/api/v1/auth/login",
        json={"email": user_a_email, "password": "PassA123!"},
    )
    assert res_old.status_code == 401

    # 3. Login with new password must succeed
    res_new = client.post(
        "/api/v1/auth/login",
        json={"email": user_a_email, "password": "NewStrongPass2026!"},
    )
    assert res_new.status_code == 200
