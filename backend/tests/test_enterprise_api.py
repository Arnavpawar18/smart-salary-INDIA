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
from app.models.employee import Employee
from app.models.organization import Organization, OrganizationMembership
from app.models.payroll import PayrollPeriod, PayrollRun
from app.seeds.seed_reference_data import seed_reference_data

client = TestClient(app)


@pytest.fixture
def enterprise_api_fixture():
    """Sets up a complete enterprise organization with HR user and payroll runs."""
    with SessionLocal() as db:
        seed_reference_data(db)

        role_hr = db.scalar(select(Role).where(Role.name == "HR_MANAGER"))

        # 1. Organization
        org = Organization(
            legal_name="Enterprise Apex Corp",
            display_name="Enterprise Apex",
            organization_code=f"APEX_{uuid.uuid4().hex[:6]}",
            status="ACTIVE",
        )
        db.add(org)
        db.flush()

        # 2. User & Membership
        user = User(
            email=f"admin_{uuid.uuid4().hex[:6]}@apex.com",
            hashed_password=PasswordHasher.hash_password("PassApex123!"),
            full_name="Apex Administrator",
        )
        db.add(user)
        db.flush()
        if role_hr:
            db.execute(user_roles.insert().values(user_id=user.id, role_id=role_hr.id))

        mem = OrganizationMembership(
            user_id=user.id,
            organization_id=org.id,
            role_id=role_hr.id if role_hr else 1,
            status="ACTIVE",
        )
        db.add(mem)

        # 3. Employee
        emp = Employee(
            organization_id=org.id,
            user_id=user.id,
            employee_code=f"EMP-APX-{uuid.uuid4().hex[:4]}",
            first_name="Apex",
            last_name="Staff",
            email=user.email,
            date_of_joining=date(2025, 4, 1),
            state_id=1,
        )
        db.add(emp)

        # 4. Payroll Period & Run
        period = PayrollPeriod(
            organization_id=org.id,
            financial_year="2026-27",
            period_code=f"2026-04-{uuid.uuid4().hex[:4]}",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
            pay_date=date(2026, 4, 30),
            status="CALCULATED",
        )
        db.add(period)
        db.flush()

        run = PayrollRun(
            organization_id=org.id,
            payroll_period_id=period.id,
            run_version=1,
            status="CALCULATED",
            total_gross_earnings=Decimal("150000.00"),
            total_net_pay=Decimal("120000.00"),
            total_employer_cost=Decimal("165000.00"),
            input_hash="a" * 64,
            result_hash="b" * 64,
        )
        db.add(run)
        db.commit()

        return {
            "org_id": org.id,
            "user_id": user.id,
            "emp_id": emp.id,
        }


def test_enterprise_dashboard_summary_api(enterprise_api_fixture):
    """
    Verifies that /api/v1/enterprise/dashboard-summary returns accurate scoped tenant metrics.
    """
    org_id = enterprise_api_fixture["org_id"]
    user_id = enterprise_api_fixture["user_id"]
    emp_id = enterprise_api_fixture["emp_id"]

    token = JWTProvider.create_access_token(user_id=user_id, role="HR_MANAGER", employee_id=emp_id)
    client.cookies.set("access_token", token)

    res = client.get(
        "/api/v1/enterprise/dashboard-summary",
        headers={"X-Organization-Id": str(org_id)},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["organization"]["id"] == org_id
    assert data["headcount"] >= 1
    assert data["latest_payroll_run"] is not None
    assert data["latest_payroll_run"]["total_gross_earnings"] == "150000.00"
    assert data["latest_payroll_run"]["total_net_pay"] == "120000.00"
