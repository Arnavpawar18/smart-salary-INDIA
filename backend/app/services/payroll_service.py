import hashlib
import json
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.calculation import CalculationSnapshot
from app.models.employee import Employee
from app.models.payroll import PayrollPeriod, PayrollRun, PayrollRunItem
from app.models.salary import SalaryRecord
from app.services.calculation_service import CalculationService


class PayrollProcessingService:
    """
    Enterprise Payroll Engine executing deterministic payroll runs.
    Enforces:
    1. Direct integration with Phase 2 CalculationService & CalculationSnapshot.
    2. Canonical Net Pay Formula:
       Total Deductions = EPF + PT + TDS + Other
       Net Pay = Gross - Total Deductions
       Employer Cost = Gross + Employer Contributions
    3. Three-View Financial Model (Employee, Employer, Statutory).
    4. Cryptographic Provenance (SHA-256) & Idempotency.
    """

    def __init__(self, db: Session):
        self.db = db
        self.calc_service = CalculationService(db)

    def calculate_payroll_run(
        self,
        organization_id: int,
        payroll_period_id: int,
        run_version: int = 1,
        created_by: int | None = None,
    ) -> PayrollRun:
        # 1. Fetch period
        period = self.db.scalar(
            select(PayrollPeriod).where(
                PayrollPeriod.id == payroll_period_id,
                PayrollPeriod.organization_id == organization_id,
            )
        )
        if not period:
            raise ValueError(f"PayrollPeriod {payroll_period_id} not found for organization {organization_id}")

        if period.status in ["LOCKED", "CLOSED"]:
            raise ValueError(f"Cannot calculate payroll for period {period.period_code} in status {period.status}")

        # 2. Check if run already exists
        existing_run = self.db.scalar(
            select(PayrollRun).where(
                PayrollRun.organization_id == organization_id,
                PayrollRun.payroll_period_id == payroll_period_id,
                PayrollRun.run_version == run_version,
            )
        )
        if existing_run and existing_run.status == "LOCKED":
            raise ValueError(f"Payroll run v{run_version} for period {period.period_code} is LOCKED.")

        if existing_run:
            # Clear existing items if re-calculating draft
            for it in existing_run.items:
                self.db.delete(it)
            self.db.flush()
            payroll_run = existing_run
        else:
            payroll_run = PayrollRun(
                organization_id=organization_id,
                payroll_period_id=payroll_period_id,
                run_version=run_version,
                status="CALCULATING",
                input_hash="PENDING",
                result_hash="PENDING",
                created_by=created_by,
            )
            self.db.add(payroll_run)
            self.db.flush()

        # 3. Fetch all active employees in organization
        employees = list(
            self.db.scalars(
                select(Employee).where(
                    Employee.organization_id == organization_id,
                    Employee.employment_status == "ACTIVE",
                )
            ).all()
        )

        tot_gross = Decimal("0.00")
        tot_emp_ded = Decimal("0.00")
        tot_tds = Decimal("0.00")
        tot_emp_pf = Decimal("0.00")
        tot_empr_pf = Decimal("0.00")
        tot_pt = Decimal("0.00")
        tot_net = Decimal("0.00")
        tot_empr_cost = Decimal("0.00")

        items_payload = []

        for emp in employees:
            # Fetch active compensation for period pay date
            active_comp = self.db.scalar(
                select(SalaryRecord).where(
                    SalaryRecord.employee_id == emp.id,
                    SalaryRecord.effective_from <= period.pay_date,
                ).order_by(SalaryRecord.effective_from.desc())
            )
            if not active_comp:
                continue

            monthly_gross = active_comp.monthly_gross
            annual_gross = active_comp.annual_ctc

            # Resolve state code
            state_code = emp.state.code if emp.state else "KA"

            from app.engine.common.enums import TaxRegime
            from app.engine.dto.salary_dto import SalaryInput

            # Execute Phase 2 authoritative calculation
            s_input = SalaryInput(
                annual_gross=annual_gross,
                financial_year=period.financial_year,
            )
            calc_result = self.calc_service.calculate_salary(
                salary_input=s_input,
                regime=TaxRegime.NEW,
                state_code=state_code,
                employee_id=emp.id,
            )

            # Monthly allocations from Phase 2 VerifiedCalculationResult
            monthly_tax = calc_result.estimated_monthly_tax
            monthly_epf = calc_result.monthly_employee_pf
            monthly_pt = calc_result.monthly_professional_tax

            # Breakdown
            basic = (monthly_gross * Decimal("0.50")).quantize(Decimal("0.01"))
            hra = (monthly_gross * Decimal("0.25")).quantize(Decimal("0.01"))
            special = monthly_gross - basic - hra

            # Deductions
            emp_ded = monthly_epf + monthly_pt + monthly_tax
            net_pay = monthly_gross - emp_ded

            # Employer
            employer_pf = calc_result.monthly_employer_contribution
            employer_eps = Decimal("0.00")
            employer_edli = Decimal("0.00")
            employer_cost = monthly_gross + employer_pf + employer_eps + employer_edli

            # Snapshot record link
            snap = self.db.scalar(
                select(CalculationSnapshot).where(
                    CalculationSnapshot.input_hash == calc_result.input_hash
                ).order_by(CalculationSnapshot.created_at.desc())
            )
            calc_run_id = snap.calculation_run_id if snap else None

            item = PayrollRunItem(
                payroll_run_id=payroll_run.id,
                employee_id=emp.id,
                calculation_run_id=calc_run_id,
                calculation_snapshot_id=snap.id if snap else None,
                monthly_gross=monthly_gross,
                basic_salary=basic,
                hra=hra,
                special_allowance=special,
                other_earnings=Decimal("0.00"),
                employee_pf=monthly_epf,
                professional_tax=monthly_pt,
                tds_deducted=monthly_tax,
                other_deductions=Decimal("0.00"),
                total_employee_deductions=emp_ded,
                net_pay=net_pay,
                employer_pf=employer_pf,
                employer_eps=employer_eps,
                employer_edli=employer_edli,
                employer_cost=employer_cost,
                days_worked=30,
                lop_days=0,
            )
            self.db.add(item)

            tot_gross += monthly_gross
            tot_emp_ded += emp_ded
            tot_tds += monthly_tax
            tot_emp_pf += monthly_epf
            tot_empr_pf += employer_pf
            tot_pt += monthly_pt
            tot_net += net_pay
            tot_empr_cost += employer_cost

            items_payload.append({
                "employee_id": emp.id,
                "gross": str(monthly_gross),
                "net": str(net_pay),
                "tds": str(monthly_tax),
                "pf": str(monthly_epf),
            })

        # Cryptographic Provenance Hash
        inp_str = json.dumps({"org_id": organization_id, "period": period.period_code, "ver": run_version, "emps": len(employees)}, sort_keys=True)
        res_str = json.dumps({"tot_gross": str(tot_gross), "tot_net": str(tot_net), "items": items_payload}, sort_keys=True)

        payroll_run.total_gross_earnings = tot_gross
        payroll_run.total_employee_deductions = tot_emp_ded
        payroll_run.total_tax_tds = tot_tds
        payroll_run.total_employee_pf = tot_emp_pf
        payroll_run.total_employer_pf = tot_empr_pf
        payroll_run.total_pt = tot_pt
        payroll_run.total_net_pay = tot_net
        payroll_run.total_employer_cost = tot_empr_cost
        payroll_run.input_hash = hashlib.sha256(inp_str.encode()).hexdigest()
        payroll_run.result_hash = hashlib.sha256(res_str.encode()).hexdigest()
        payroll_run.status = "CALCULATED"

        period.status = "CALCULATED"
        self.db.commit()
        self.db.refresh(payroll_run)
        return payroll_run
