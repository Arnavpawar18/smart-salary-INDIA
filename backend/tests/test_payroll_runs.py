import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.employee import Employee
from app.models.organization import Organization
from app.models.payroll import PayrollPeriod, PayrollRunItem
from app.models.salary import SalaryRecord
from app.seeds.seed_reference_data import seed_reference_data
from app.services.payroll_service import PayrollProcessingService


def test_payroll_run_calculation_and_three_view_model():
    """
    Verifies that PayrollProcessingService executes an end-to-end payroll run:
    1. Correct canonical net pay: Net Pay = Gross - (EPF + PT + TDS)
    2. Employer Cost = Gross + Employer Contributions
    3. Proper linkage to Phase 2 CalculationSnapshots
    4. Cryptographic provenance SHA-256 hashes generated
    """
    with SessionLocal() as db:
        seed_reference_data(db)

        # 1. Create Organization
        org = Organization(
            legal_name="Enterprise Tech Corp",
            display_name="Enterprise Tech",
            organization_code=f"ENT_{uuid.uuid4().hex[:6]}",
            status="ACTIVE",
        )
        db.add(org)
        db.flush()

        from app.models.employee import State

        ka_state = db.scalar(select(State).where(State.code == "KA"))

        # 2. Create Employees
        emp1 = Employee(
            organization_id=org.id,
            employee_code=f"EMP-E1-{uuid.uuid4().hex[:4]}",
            first_name="Alice",
            last_name="Engineer",
            email=f"alice_{uuid.uuid4().hex[:6]}@ent.com",
            date_of_joining=date(2025, 4, 1),
            state_id=ka_state.id if ka_state else 1,  # KA
        )
        emp2 = Employee(
            organization_id=org.id,
            employee_code=f"EMP-E2-{uuid.uuid4().hex[:4]}",
            first_name="Bob",
            last_name="Manager",
            email=f"bob_{uuid.uuid4().hex[:6]}@ent.com",
            date_of_joining=date(2025, 4, 1),
            state_id=ka_state.id if ka_state else 1,  # KA
        )
        db.add_all([emp1, emp2])
        db.flush()

        # 3. Create Compensations
        comp1 = SalaryRecord(
            employee_id=emp1.id,
            effective_from=date(2025, 4, 1),
            annual_ctc=Decimal("1200000.00"),
            monthly_gross=Decimal("100000.00"),
        )
        comp2 = SalaryRecord(
            employee_id=emp2.id,
            effective_from=date(2025, 4, 1),
            annual_ctc=Decimal("2400000.00"),
            monthly_gross=Decimal("200000.00"),
        )
        db.add_all([comp1, comp2])
        db.flush()

        # 4. Create Payroll Period for April 2026 (FY 2026-27)
        period = PayrollPeriod(
            organization_id=org.id,
            financial_year="2026-27",
            period_code=f"2026-04-{uuid.uuid4().hex[:4]}",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
            pay_date=date(2026, 4, 30),
            status="OPEN",
        )
        db.add(period)
        db.commit()
        db.refresh(period)

        # 5. Execute Payroll Calculation
        payroll_svc = PayrollProcessingService(db)
        payroll_run = payroll_svc.calculate_payroll_run(
            organization_id=org.id,
            payroll_period_id=period.id,
            run_version=1,
        )

        assert payroll_run.id is not None
        assert payroll_run.status == "CALCULATED"
        assert len(payroll_run.input_hash) == 64
        assert len(payroll_run.result_hash) == 64

        # Verify Line Items
        items = list(db.scalars(select(PayrollRunItem).where(PayrollRunItem.payroll_run_id == payroll_run.id)).all())
        assert len(items) == 2

        for item in items:
            # Canonical Net Pay Formula check: Net = Gross - Total Deductions
            assert item.net_pay == item.monthly_gross - item.total_employee_deductions
            assert item.total_employee_deductions == item.employee_pf + item.professional_tax + item.tds_deducted
            # Employer cost invariant: Employer Cost = Gross + Employer Contributions
            assert item.employer_cost == item.monthly_gross + item.employer_pf + item.employer_eps + item.employer_edli
            # Direct link to Phase 2 Snapshot
            assert item.calculation_run_id is not None
            assert item.calculation_snapshot_id is not None

        # Verify Period Status
        db.refresh(period)
        assert period.status == "CALCULATED"
