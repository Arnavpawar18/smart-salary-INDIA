"""
Milestone M11.1: Company Payroll End-to-End Flow
Executes full enterprise lifecycle: Org Creation -> Employee Onboarding -> Salary Assignment -> Payroll Run -> Snapshot Linkage.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.employee import Employee, State
from app.models.organization import Organization
from app.models.payroll import PayrollPeriod
from app.models.salary import SalaryRecord
from app.seeds.seed_reference_data import seed_reference_data
from app.services.payroll_service import PayrollProcessingService


def test_m11_company_payroll_e2e():
    with SessionLocal() as db:
        seed_reference_data(db)

        # 1. Organization
        org = Organization(
            legal_name="M11 Enterprise Systems Inc",
            display_name="M11 Enterprise",
            organization_code=f"M11_{uuid.uuid4().hex[:6]}",
            status="ACTIVE",
        )
        db.add(org)
        db.flush()

        ka_state = db.scalar(select(State).where(State.code == "KA"))

        # 2. Employees
        emp = Employee(
            organization_id=org.id,
            employee_code=f"EMP-M11-{uuid.uuid4().hex[:4]}",
            first_name="Priya",
            last_name="Sharma",
            email=f"priya_{uuid.uuid4().hex[:6]}@m11.com",
            date_of_joining=date(2025, 4, 1),
            state_id=ka_state.id if ka_state else 1,
        )
        db.add(emp)
        db.flush()

        # 3. Compensation Record
        comp = SalaryRecord(
            employee_id=emp.id,
            effective_from=date(2025, 4, 1),
            annual_ctc=Decimal("1800000.00"),
            monthly_gross=Decimal("150000.00"),
        )
        db.add(comp)
        db.flush()

        # 4. Payroll Period
        period = PayrollPeriod(
            organization_id=org.id,
            financial_year="2026-27",
            period_code=f"2026-05-{uuid.uuid4().hex[:4]}",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 31),
            pay_date=date(2026, 5, 31),
            status="OPEN",
        )
        db.add(period)
        db.commit()

        # 5. Process Payroll
        payroll_svc = PayrollProcessingService(db)
        payroll_run = payroll_svc.calculate_payroll_run(
            organization_id=org.id,
            payroll_period_id=period.id,
            run_version=1,
        )

        assert payroll_run.status == "CALCULATED"
        assert payroll_run.total_gross_earnings == Decimal("150000.00")
        assert payroll_run.total_net_pay > Decimal("0.00")
        assert len(payroll_run.input_hash) == 64
        assert len(payroll_run.result_hash) == 64
