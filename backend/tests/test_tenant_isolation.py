import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import PasswordHasher
from app.core.tenant_context import get_tenant_context
from app.main import app
from app.models.auth import Role, User, user_roles
from app.models.employee import Department, Employee
from app.models.organization import Organization, OrganizationMembership
from app.seeds.seed_reference_data import seed_reference_data

client = TestClient(app)


@pytest.fixture
def multi_tenant_fixture():
    """Sets up two isolated organizations with dedicated users and memberships."""
    with SessionLocal() as db:
        seed_reference_data(db)

        role_hr = db.scalar(select(Role).where(Role.name == "HR_MANAGER"))
        role_emp = db.scalar(select(Role).where(Role.name == "EMPLOYEE"))

        # 1. Organization Alpha
        org_a = Organization(
            legal_name="Alpha Corp India Pvt Ltd",
            display_name="Alpha Corp",
            organization_code=f"ALPHA_{uuid.uuid4().hex[:6]}",
            status="ACTIVE",
        )
        db.add(org_a)
        db.flush()

        user_a = User(
            email=f"hr_a_{uuid.uuid4().hex[:6]}@alpha.com",
            hashed_password=PasswordHasher.hash_password("PassA123!"),
            full_name="Alpha HR",
        )
        db.add(user_a)
        db.flush()
        if role_hr:
            db.execute(user_roles.insert().values(user_id=user_a.id, role_id=role_hr.id))

        mem_a = OrganizationMembership(user_id=user_a.id, organization_id=org_a.id, role_id=role_hr.id, status="ACTIVE")
        db.add(mem_a)

        dept_a = Department(
            organization_id=org_a.id, name=f"Engineering A {uuid.uuid4().hex[:4]}", code=f"ENG-A-{uuid.uuid4().hex[:4]}"
        )
        db.add(dept_a)
        db.flush()

        emp_a = Employee(
            organization_id=org_a.id,
            user_id=user_a.id,
            employee_code=f"EMP-A-{user_a.id:04d}",
            first_name="Alpha",
            last_name="Staff",
            email=user_a.email,
            department_id=dept_a.id,
            date_of_joining=date(2026, 4, 1),
            state_id=1,
        )
        db.add(emp_a)

        # 2. Organization Beta
        org_b = Organization(
            legal_name="Beta Logistics Ltd",
            display_name="Beta Logistics",
            organization_code=f"BETA_{uuid.uuid4().hex[:6]}",
            status="ACTIVE",
        )
        db.add(org_b)
        db.flush()

        user_b = User(
            email=f"emp_b_{uuid.uuid4().hex[:6]}@beta.com",
            hashed_password=PasswordHasher.hash_password("PassB123!"),
            full_name="Beta Employee",
        )
        db.add(user_b)
        db.flush()
        if role_emp:
            db.execute(user_roles.insert().values(user_id=user_b.id, role_id=role_emp.id))

        mem_b = OrganizationMembership(
            user_id=user_b.id, organization_id=org_b.id, role_id=role_emp.id if role_emp else 1, status="ACTIVE"
        )
        db.add(mem_b)

        dept_b = Department(
            organization_id=org_b.id, name=f"Operations B {uuid.uuid4().hex[:4]}", code=f"OPS-B-{uuid.uuid4().hex[:4]}"
        )
        db.add(dept_b)
        db.flush()

        emp_b = Employee(
            organization_id=org_b.id,
            user_id=user_b.id,
            employee_code=f"EMP-B-{user_b.id:04d}",
            first_name="Beta",
            last_name="Staff",
            email=user_b.email,
            department_id=dept_b.id,
            date_of_joining=date(2026, 4, 1),
            state_id=1,
        )
        db.add(emp_b)

        db.commit()

        return {
            "org_a_id": org_a.id,
            "user_a_id": user_a.id,
            "emp_a_id": emp_a.id,
            "org_b_id": org_b.id,
            "user_b_id": user_b.id,
            "emp_b_id": emp_b.id,
        }


def test_tenant_context_resolution(multi_tenant_fixture):
    """
    Verifies that get_tenant_context resolves valid tenant membership and blocks cross-tenant access.
    """
    user_a_id = multi_tenant_fixture["user_a_id"]
    org_a_id = multi_tenant_fixture["org_a_id"]
    org_b_id = multi_tenant_fixture["org_b_id"]

    with SessionLocal() as db:
        user_a = db.scalar(select(User).where(User.id == user_a_id))

        # 1. Valid resolution for Org A
        ctx_a = get_tenant_context(current_user=user_a, x_organization_id=str(org_a_id), db=db)
        assert ctx_a.organization_id == org_a_id
        assert ctx_a.role_name == "HR_MANAGER"

        # 2. Cross-tenant attempt to access Org B receives 403 Forbidden
        with pytest.raises(Exception) as exc_info:
            get_tenant_context(current_user=user_a, x_organization_id=str(org_b_id), db=db)
        assert "403" in str(exc_info.value) or "Access denied" in str(exc_info.value)
