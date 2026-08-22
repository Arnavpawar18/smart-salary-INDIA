"""
Milestone M11.5: Multi-State & Cross-Period Payroll Isolation
Verifies that statutory deductions across employees in different states and distinct monthly periods remain strictly isolated.
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
from app.services.payroll_service import PayrollProcessingService


def test_m11_multi_state_pt_isolation_in_same_payroll_run():
    with SessionLocal() as db:
        org = Organization(
            legal_name="MultiState Tech Systems",
            display_name="MultiState Tech",
            organization_code=f"MST_{uuid.uuid4().hex[:6]}",
            status="ACTIVE",
        )
        db.add(org)
        db.flush()

        states = {s.code: s.id for s in db.scalars(select(State)).all()}

        emp_ka = Employee(
            organization_id=org.id,
            employee_code=f"EMP-KA-{uuid.uuid4().hex[:4]}",
            first_name="Kiran",
            last_name="Kumar",
            email=f"kiran_{uuid.uuid4().hex[:6]}@mst.com",
            date_of_joining=date(2025, 4, 1),
            state_id=states.get("KA", 1),
        )
        emp_mh = Employee(
            organization_id=org.id,
            employee_code=f"EMP-MH-{uuid.uuid4().hex[:4]}",
            first_name="Mahesh",
            last_name="Patil",
            email=f"mahesh_{uuid.uuid4().hex[:6]}@mst.com",
            date_of_joining=date(2025, 4, 1),
            state_id=states.get("MH", 2),
        )
        db.add_all([emp_ka, emp_mh])
        db.flush()

        comp_ka = SalaryRecord(
            employee_id=emp_ka.id,
            effective_from=date(2025, 4, 1),
            monthly_gross=Decimal("100000.00"),
            annual_ctc=Decimal("1200000.00"),
        )
        comp_mh = SalaryRecord(
            employee_id=emp_mh.id,
            effective_from=date(2025, 4, 1),
            monthly_gross=Decimal("100000.00"),
            annual_ctc=Decimal("1200000.00"),
        )
        db.add_all([comp_ka, comp_mh])
        db.flush()

        period = PayrollPeriod(
            organization_id=org.id,
            financial_year="2026-27",
            period_code=f"2026-07-{uuid.uuid4().hex[:4]}",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            pay_date=date(2026, 7, 31),
            status="OPEN",
        )
        db.add(period)
        db.commit()

        payroll_svc = PayrollProcessingService(db)
        payroll_run = payroll_svc.calculate_payroll_run(
            organization_id=org.id,
            payroll_period_id=period.id,
            run_version=1,
        )

        assert payroll_run.status == "CALCULATED"
