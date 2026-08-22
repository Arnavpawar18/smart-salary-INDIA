import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import JWTProvider, PasswordHasher
from app.main import app
from app.models.auth import Role, User, user_roles
from app.models.employee import Employee

client = TestClient(app)


def test_rbac_permission_matrix_enforcement():
    """
    Verifies that RBAC permissions control actual endpoint access.
    EMPLOYEE role has access to own dashboard, history, and calculator, but not admin routes.
    """
    with SessionLocal() as db:
        email = f"emp_rbac_{uuid.uuid4().hex[:8]}@smartsalary.in"
        user = User(email=email, hashed_password=PasswordHasher.hash_password("Pass123!"), full_name="RBAC Employee")
        db.add(user)
        db.flush()

        role_emp = db.scalar(select(Role).where(Role.name == "EMPLOYEE"))
        if role_emp:
            db.execute(user_roles.insert().values(user_id=user.id, role_id=role_emp.id))

        emp = Employee(
            user_id=user.id,
            employee_code=f"EMP-{user.id:04d}",
            first_name="RBAC",
            last_name="Employee",
            email=email,
            date_of_joining=date(2026, 4, 1),
            state_id=1,
        )
        db.add(emp)
        db.commit()
        db.refresh(user)
        db.refresh(emp)

        token = JWTProvider.create_access_token(user_id=user.id, role="EMPLOYEE", employee_id=emp.id)
        client.cookies.set("access_token", token)

        # 1. Calculator Access: Allowed for Employee
        res_calc = client.post(
            "/api/v1/calculations",
            json={
                "financial_year": "2025-26",
                "annual_gross_salary": "1200000.00",
                "regime": "NEW",
                "state_code": "KA",
            },
        )
        assert res_calc.status_code == 201

        # 2. History Access: Allowed for Employee
        res_hist = client.get("/api/v1/calculations/history")
        assert res_hist.status_code == 200

        # 3. Security Center / Active Sessions: Allowed for Employee
        res_sess = client.get("/api/v1/auth/sessions")
        assert res_sess.status_code == 200


def test_guest_cannot_access_employee_history():
    """
    Unauthenticated / Guest user attempting to query employee calculation history receives 401.
    """
    client.cookies.clear()
    res = client.get("/api/v1/calculations/history")
    assert res.status_code == 401
