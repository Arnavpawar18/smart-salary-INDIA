import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import JWTProvider, PasswordHasher
from app.main import app
from app.models.auth import Role, User, user_roles
from app.models.compliance import TaxDeclaration
from app.models.employee import Employee
from app.models.organization import Organization, OrganizationMembership
from app.seeds.seed_reference_data import seed_reference_data

client = TestClient(app)


@pytest.fixture
def enterprise_rbac_fixture():
    with SessionLocal() as db:
        seed_reference_data(db)

        role_admin = db.scalar(select(Role).where(Role.name == "COMPANY_ADMIN"))

        # Organization
        org = Organization(
            legal_name="Enterprise Test Corp",
            display_name="Enterprise Test",
            organization_code=f"TEST_{uuid.uuid4().hex[:6]}",
            status="ACTIVE",
        )
        db.add(org)
        db.flush()

        # User & Membership (Admin / Checker)
        user = User(
            email=f"admin_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password=PasswordHasher.hash_password("PassTest123!"),
            full_name="Test Administrator",
        )
        db.add(user)
        db.flush()
        if role_admin:
            db.execute(user_roles.insert().values(user_id=user.id, role_id=role_admin.id))

        mem = OrganizationMembership(
            user_id=user.id,
            organization_id=org.id,
            role_id=role_admin.id if role_admin else 1,
            status="ACTIVE",
        )
        db.add(mem)

        emp_admin = Employee(
            organization_id=org.id,
            user_id=user.id,
            employee_code=f"EMP-ADM-{uuid.uuid4().hex[:4]}",
            first_name="Admin",
            last_name="Checker",
            email=user.email,
            date_of_joining=date(2025, 4, 1),
            state_id=1,
        )
        db.add(emp_admin)
        db.flush()

        # Staff User (Maker)
        staff_user = User(
            email=f"staff_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password=PasswordHasher.hash_password("PassTest123!"),
            full_name="Test Staff Maker",
        )
        db.add(staff_user)
        db.flush()

        emp_staff = Employee(
            organization_id=org.id,
            user_id=staff_user.id,
            employee_code=f"EMP-STF-{uuid.uuid4().hex[:4]}",
            first_name="Test",
            last_name="Staff",
            email=staff_user.email,
            date_of_joining=date(2025, 4, 1),
            state_id=1,
        )
        db.add(emp_staff)

        mem_staff = OrganizationMembership(
            user_id=staff_user.id,
            organization_id=org.id,
            role_id=role_admin.id if role_admin else 1,
            status="ACTIVE",
        )
        db.add(mem_staff)
        db.flush()

        # Declaration created by Staff Maker
        decl = TaxDeclaration(
            employee_id=emp_staff.id,
            organization_id=org.id,
            financial_year="2025-26",
            regime="NEW",
            status="SUBMITTED",
            total_declared_deductions=Decimal("150000.00"),
        )
        db.add(decl)
        db.commit()

        return {
            "org_id": org.id,
            "user_id": user.id,
            "staff_user_id": staff_user.id,
            "emp_id": emp_admin.id,
            "emp_staff_id": emp_staff.id,
            "decl_id": decl.id,
        }


def test_enterprise_risk_engine_api(enterprise_rbac_fixture):
    org_id = enterprise_rbac_fixture["org_id"]
    user_id = enterprise_rbac_fixture["user_id"]
    emp_id = enterprise_rbac_fixture["emp_id"]

    token = JWTProvider.create_access_token(user_id=user_id, role="COMPANY_ADMIN", employee_id=emp_id)
    client.cookies.set("access_token", token)

    res = client.get("/api/v1/enterprise/risk-metrics", headers={"X-Organization-Id": str(org_id)})
    assert res.status_code == 200
    data = res.json()
    assert "risk_index" in data
    assert "anomalies" in data
    assert "department_heatmap" in data
    assert "ai_insights" in data


def test_enterprise_tax_analytics_api(enterprise_rbac_fixture):
    org_id = enterprise_rbac_fixture["org_id"]
    user_id = enterprise_rbac_fixture["user_id"]
    emp_id = enterprise_rbac_fixture["emp_id"]

    token = JWTProvider.create_access_token(user_id=user_id, role="COMPANY_ADMIN", employee_id=emp_id)
    client.cookies.set("access_token", token)

    res = client.get("/api/v1/enterprise/tax-analytics", headers={"X-Organization-Id": str(org_id)})
    assert res.status_code == 200
    data = res.json()
    assert "total_tax_liability_ytd" in data
    assert "deduction_distribution" in data
    assert "departmental_compliance" in data


def test_enterprise_approvals_api_and_state_machine(enterprise_rbac_fixture):
    org_id = enterprise_rbac_fixture["org_id"]
    admin_user_id = enterprise_rbac_fixture["user_id"]
    staff_user_id = enterprise_rbac_fixture["staff_user_id"]
    admin_emp_id = enterprise_rbac_fixture["emp_id"]
    staff_emp_id = enterprise_rbac_fixture["emp_staff_id"]
    decl_id = enterprise_rbac_fixture["decl_id"]

    from app.core.auth_middleware import CSRFProtection

    csrf = CSRFProtection.generate_csrf_token()
    client.cookies.set("csrf_token", csrf)

    # 1. Maker cannot approve own request (Separation of Duties)
    maker_token = JWTProvider.create_access_token(user_id=staff_user_id, role="COMPANY_ADMIN", employee_id=staff_emp_id)
    client.cookies.set("access_token", maker_token)
    res_maker_approve = client.post(
        f"/api/v1/enterprise/approvals/{decl_id}/action",
        headers={"X-Organization-Id": str(org_id), "X-CSRF-Token": csrf},
        json={"action": "APPROVE", "remarks": "Self-approval attempt"},
    )
    assert res_maker_approve.status_code == 403
    assert "Separation of duties" in res_maker_approve.json()["detail"]

    # 2. Checker (Admin) lists approvals
    admin_token = JWTProvider.create_access_token(user_id=admin_user_id, role="COMPANY_ADMIN", employee_id=admin_emp_id)
    client.cookies.set("access_token", admin_token)

    res_list = client.get("/api/v1/enterprise/approvals", headers={"X-Organization-Id": str(org_id)})
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) >= 1

    # 3. Checker approves declaration with valid CSRF
    res_action = client.post(
        f"/api/v1/enterprise/approvals/{decl_id}/action",
        headers={"X-Organization-Id": str(org_id), "X-CSRF-Token": csrf},
        json={"action": "APPROVE", "remarks": "Proofs verified"},
    )
    assert res_action.status_code == 200
    data = res_action.json()
    assert data["new_status"] == "VERIFIED"


def test_employee_tax_center_api(enterprise_rbac_fixture):
    user_id = enterprise_rbac_fixture["user_id"]
    emp_id = enterprise_rbac_fixture["emp_id"]

    token = JWTProvider.create_access_token(user_id=user_id, role="EMPLOYEE", employee_id=emp_id)
    client.cookies.set("access_token", token)

    res = client.get("/api/v1/employee-portal/tax-center")
    assert res.status_code == 200
    data = res.json()
    assert "financial_year" in data
    assert "sections" in data
    assert "80C" in data["sections"]
    assert "ai_recommendations" in data
