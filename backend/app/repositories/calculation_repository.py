from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.dto.result_dto import VerifiedCalculationResult
from app.models.calculation import (
    CalculationLineItem,
    CalculationRun,
    CalculationSnapshot,
    CalculationTrace,
)
from app.models.pf import PFRuleVersion
from app.models.pt import ProfessionalTaxRuleVersion
from app.models.tax import TaxRuleVersion


class CalculationRepository:
    """Persists calculation runs, snapshots, line items, and traces to PostgreSQL."""

    def __init__(self, db: Session):
        self.db = db

    def save_verified_calculation(
        self,
        result: VerifiedCalculationResult,
        employee_id: Optional[int] = None,
    ) -> CalculationRun:
        # 1. Create CalculationRun
        run = CalculationRun(
            employee_id=employee_id,
            financial_year=result.financial_year,
            regime=result.regime.value,
            gross_salary=result.annual_gross_salary,
            taxable_income=result.taxable_income,
            total_tax=result.total_annual_tax_liability,
            total_pf_employee=result.annual_employee_pf,
            total_pf_employer=result.annual_employer_contribution,
            total_professional_tax=result.annual_professional_tax,
            net_take_home=result.estimated_annual_take_home,
            status=result.status.value,
        )
        self.db.add(run)
        self.db.flush()

        # Look up rule version IDs
        trv_id = self.db.scalar(select(TaxRuleVersion.id).where(TaxRuleVersion.version_code == result.tax_rule_version_code))
        pfrv_id = self.db.scalar(select(PFRuleVersion.id).where(PFRuleVersion.version_code == result.pf_rule_version_code))
        ptrv_id = self.db.scalar(select(ProfessionalTaxRuleVersion.id).where(ProfessionalTaxRuleVersion.version_code == result.pt_rule_version_code))

        # 2. Create CalculationSnapshot
        snapshot = CalculationSnapshot(
            calculation_run_id=run.id,
            input_snapshot={
                "financial_year": result.financial_year,
                "regime": result.regime.value,
                "state_code": result.state_code,
                "annual_gross": f"{result.annual_gross_salary:.2f}",
                "assumptions": result.assumptions.to_dict(),
            },
            result_snapshot=result.to_dict(),
            input_hash=result.input_hash,
            result_hash=result.result_hash,
            engine_version=result.engine_version,
            tax_rule_version_id=trv_id,
            pf_rule_version_id=pfrv_id,
            professional_tax_rule_version_id=ptrv_id,
            rounding_policy_version=result.rounding_policy_version,
        )
        self.db.add(snapshot)
        self.db.flush()

        # 3. Create CalculationLineItems
        line_item_objs = []
        for li in result.line_items:
            obj = CalculationLineItem(
                calculation_run_id=run.id,
                sequence_order=li.sequence,
                component_type=li.category.value,
                name=li.item_type.value,
                amount=li.amount,
                rate=li.rate,
                description=li.description,
            )
            self.db.add(obj)
            line_item_objs.append(obj)
        self.db.flush()

        # 4. Create CalculationTraces
        for idx, step in enumerate(result.trace_steps, 1):
            trace = CalculationTrace(
                calculation_run_id=run.id,
                step_order=step.step_number,
                step_name=step.title,
                formula=step.formula,
                input_values=step.inputs,
                output_values=step.outputs,
                explanation=step.description,
                legal_reference=step.legal_reference,
            )
            self.db.add(trace)

        self.db.commit()
        self.db.refresh(run)
        return run
