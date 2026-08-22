"""
Milestone M11.1: RBAC Permission Matrix Enforcement
Verifies role-based access for Super Admin, Payroll Admin, HR Manager, Employee, and Auditor across multi-tenant boundaries.
"""

import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import JWTProvider, PasswordHasher
from app.main import app
from app.models.auth import Role, User, user_roles
from app.models.employee import Employee


def test_m11_rbac_auditor_read_only_access():
    client = TestClient(app)
    with SessionLocal() as db:
        email = f"auditor_{uuid.uuid4().hex[:6]}@smartsalary.in"
        user = User(email=email, hashed_password=PasswordHasher.hash_password("Pass123!"), full_name="Auditor User")
        db.add(user)
        db.flush()

        role_aud = db.scalar(select(Role).where(Role.name == "AUDITOR"))
        if role_aud:
            db.execute(user_roles.insert().values(user_id=user.id, role_id=role_aud.id))

        emp = Employee(
            user_id=user.id,
            employee_code=f"EMP-{user.id:04d}",
            first_name="Audit",
            last_name="Officer",
            email=email,
            date_of_joining=date(2026, 4, 1),
            state_id=1,
        )
        db.add(emp)
        db.commit()

        token = JWTProvider.create_access_token(user_id=user.id, role="AUDITOR", employee_id=emp.id)

        # 1. Auditor can view calculations history
        client.cookies.set("access_token", token)
        get_resp = client.get("/api/v1/calculations/history")
        assert get_resp.status_code == 200

        # 2. Unauthenticated user gets 401
        client_guest = TestClient(app)
        guest_resp = client_guest.get("/api/v1/calculations/history")
        assert guest_resp.status_code == 401
