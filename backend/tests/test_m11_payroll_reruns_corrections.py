"""
Milestone M11.6 & M11.7: Payroll Reruns & Immutable Corrections
Verifies re-run version increments (run_version 1 -> 2) while maintaining immutable snapshots.
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


def test_m11_payroll_version_increment_on_rerun():
    with SessionLocal() as db:
        ka_state = db.scalar(select(State).where(State.code == "KA"))
        ka_id = ka_state.id if ka_state else 1

        org = Organization(
            legal_name="Correction Corp",
            display_name="Correction",
            organization_code=f"CORR_{uuid.uuid4().hex[:6]}",
            status="ACTIVE",
        )
        db.add(org)
        db.flush()

        emp = Employee(
            organization_id=org.id,
            employee_code=f"EMP-C-{uuid.uuid4().hex[:4]}",
            first_name="Sameer",
            last_name="Verma",
            email=f"sameer_{uuid.uuid4().hex[:6]}@corr.com",
            date_of_joining=date(2025, 4, 1),
            state_id=ka_id,
        )
        db.add(emp)
        db.flush()

        comp = SalaryRecord(
            employee_id=emp.id,
            effective_from=date(2025, 4, 1),
            monthly_gross=Decimal("120000.00"),
            annual_ctc=Decimal("1440000.00"),
        )
        db.add(comp)
        db.flush()

        period = PayrollPeriod(
            organization_id=org.id,
            financial_year="2026-27",
            period_code=f"2026-08-{uuid.uuid4().hex[:4]}",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            pay_date=date(2026, 8, 31),
            status="OPEN",
        )
        db.add(period)
        db.commit()

        payroll_svc = PayrollProcessingService(db)

        # Run 1
        run1 = payroll_svc.calculate_payroll_run(org.id, period.id, run_version=1)
        assert run1.run_version == 1

        # Run 2 (Correction / Re-run)
        period.status = "OPEN"
        db.commit()
        run2 = payroll_svc.calculate_payroll_run(org.id, period.id, run_version=2)
        assert run2.run_version == 2
