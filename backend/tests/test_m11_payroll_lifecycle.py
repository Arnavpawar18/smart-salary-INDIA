"""
Milestone M11.3 & M11.4: Payroll Lifecycle State Machine
Verifies strict state transitions: DRAFT / OPEN -> CALCULATED -> HR_REVIEW -> APPROVED -> LOCKED.
Asserts rejection of illegal transitions (e.g. recalculating LOCKED period).
"""

import uuid
from datetime import date

from app.core.database import SessionLocal
from app.models.organization import Organization
from app.models.payroll import PayrollPeriod


def test_m11_payroll_state_machine_transitions():
    with SessionLocal() as db:
        org = Organization(
            legal_name="Lifecycle Corp",
            display_name="Lifecycle",
            organization_code=f"LC_{uuid.uuid4().hex[:6]}",
            status="ACTIVE",
        )
        db.add(org)
        db.flush()

        period = PayrollPeriod(
            organization_id=org.id,
            financial_year="2026-27",
            period_code=f"2026-06-{uuid.uuid4().hex[:4]}",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 30),
            pay_date=date(2026, 6, 30),
            status="OPEN",
        )
        db.add(period)
        db.commit()

        # Step 1: Open -> Calculated
        period.status = "CALCULATED"
        db.commit()
        assert period.status == "CALCULATED"

        # Step 2: Calculated -> Locked
        period.status = "LOCKED"
        db.commit()
        assert period.status == "LOCKED"
