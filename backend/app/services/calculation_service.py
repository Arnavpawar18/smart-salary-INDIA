from decimal import Decimal

from sqlalchemy.orm import Session

from app.engine.common.enums import CalculationStatus, TaxRegime
from app.engine.common.hashing import compute_sha256_hash
from app.engine.common.money import quantize_currency
from app.engine.common.rounding import DEFAULT_ROUNDING_POLICY
from app.engine.dto.pf_dto import PfCalculationInput
from app.engine.dto.pt_dto import PtCalculationInput
from app.engine.dto.result_dto import (
    CalculationAssumptions,
    RegimeComparisonResult,
    VerifiedCalculationResult,
)
from app.engine.dto.salary_dto import SalaryInput
from app.engine.dto.tax_dto import TaxCalculationInput
from app.engine.normalizer.salary_normalizer import SalaryNormalizer
from app.engine.pf.pf_calculator import PfCalculator
from app.engine.professional_tax.pt_calculator import PtCalculator
from app.engine.tax.tax_calculator import TaxCalculator
from app.engine.trace.trace_builder import TraceBuilder
from app.engine.validation.invariants import FinancialInvariantsValidator
from app.repositories.calculation_repository import CalculationRepository
from app.services.rule_applicability import RuleApplicabilityResolver


class CalculationService:
    """
    Authoritative calculation orchestrator.
    Flow: Input -> Normalizer -> Rules Resolver -> Pure Engines (Tax, PF, PT)
    -> Invariant Validation -> Trace -> Snapshot -> DB Persistence -> VerifiedResult.
    """

    ENGINE_VERSION = "CALC-1.0.0"

    def __init__(self, db: Session):
        self.db = db
        self.resolver = RuleApplicabilityResolver(db)
        self.calc_repo = CalculationRepository(db)

    def calculate_salary(
        self,
        salary_input: SalaryInput,
        regime: TaxRegime,
        state_code: str,
        age: int = 25,
        employee_id: int | None = None,
        persist: bool = True,
    ) -> VerifiedCalculationResult:
        # 1. Normalize Salary Input
        normalized = SalaryNormalizer.normalize(salary_input)

        # 2. Resolve Statutory Rules (Tax, PF, PT)
        tax_rules, pf_rules, pt_rules = self.resolver.resolve_all(
            financial_year=salary_input.financial_year,
            regime=regime,
            state_code=state_code,
        )

        # 3. Pure Tax Calculation
        tax_inp = TaxCalculationInput(
            financial_year=salary_input.financial_year,
            regime=regime,
            annual_gross_salary=normalized.annual_gross,
            age=age,
        )
        tax_res = TaxCalculator.calculate_tax(tax_inp, tax_rules)

        # 4. Pure PF Calculation
        pf_inp = PfCalculationInput(
            pf_wage_base_monthly=normalized.pf_wage_base_monthly,
            is_pf_applicable=True,
            opt_in_higher_wage=salary_input.pf_opt_in_higher_wage,
        )
        pf_res = PfCalculator.calculate_pf(pf_inp, pf_rules)

        # 5. Pure PT Calculation
        pt_inp = PtCalculationInput(
            state_code=state_code,
            monthly_gross_salary=normalized.monthly_gross,
        )
        pt_res = PtCalculator.calculate_pt(pt_inp, pt_rules)

        # 6. Build Trace & Ledger
        line_items, trace_steps = TraceBuilder.build_ledger_and_trace(
            salary=normalized,
            tax_res=tax_res,
            pf_res=pf_res,
            pt_res=pt_res,
            tax_rules=tax_rules,
            pf_rules=pf_rules,
            pt_rules=pt_rules,
        )

        # 7. Compute Net Take-home & Reconcile Invariants
        total_tax = tax_res["total_annual_tax_liability"]
        emp_pf = pf_res.annual_employee_epf
        ann_pt = pt_res.annual_pt
        other_ded = normalized.other_employee_deductions

        take_home_annual = normalized.annual_gross - total_tax - emp_pf - ann_pt - other_ded
        take_home_monthly = quantize_currency(take_home_annual / Decimal("12"))

        FinancialInvariantsValidator.validate(
            salary=normalized,
            total_tax=total_tax,
            employee_pf=emp_pf,
            annual_pt=ann_pt,
            take_home_annual=take_home_annual,
        )

        # 8. Construct Assumptions and Provenance Hashes
        assumptions = CalculationAssumptions(
            salary_income_only=True,
            residential_status="RESIDENT",
            age=age,
            state=state_code,
            pf_applicable=True,
            pf_opt_in_higher_wage=salary_input.pf_opt_in_higher_wage,
            tds_provided=False,
            other_income_provided=False,
            notes=[
                "Calculated based on salary income only without additional Chapter VI-A investment declarations unless specified.",
                "Estimated annual tax liability is computed before considering TDS already deducted by employer.",
            ],
        )

        raw_input_dict = {
            "financial_year": salary_input.financial_year,
            "regime": regime.value,
            "state_code": state_code,
            "annual_gross": f"{normalized.annual_gross:.2f}",
            "age": age,
        }
        input_hash = compute_sha256_hash(raw_input_dict)

        raw_result_summary = {
            "gross": f"{normalized.annual_gross:.2f}",
            "taxable_income": f"{tax_res['taxable_income']:.2f}",
            "tax": f"{total_tax:.2f}",
            "pf": f"{emp_pf:.2f}",
            "pt": f"{ann_pt:.2f}",
            "take_home": f"{take_home_annual:.2f}",
        }
        result_hash = compute_sha256_hash(raw_result_summary)

        # Combined rule set hash
        combined_rule_hash = compute_sha256_hash(
            tax_rules.rule_set_hash + pf_rules.rule_set_hash + pt_rules.rule_set_hash
        )

        verified_result = VerifiedCalculationResult(
            engine_version=self.ENGINE_VERSION,
            rounding_policy_version=DEFAULT_ROUNDING_POLICY.policy_version,
            status=CalculationStatus.VERIFIED,
            financial_year=salary_input.financial_year,
            regime=regime,
            state_code=state_code,
            annual_gross_salary=normalized.annual_gross,
            standard_deduction=tax_res["standard_deduction"],
            taxable_income=tax_res["taxable_income"],
            slab_tax=tax_res["slab_tax"],
            section_87a_rebate=tax_res["section_87a_rebate"],
            rebate_marginal_relief=tax_res["rebate_marginal_relief"],
            tax_after_rebate=tax_res["tax_after_rebate"],
            surcharge=tax_res["surcharge"],
            surcharge_marginal_relief=tax_res["surcharge_marginal_relief"],
            health_education_cess=tax_res["health_education_cess"],
            total_annual_tax_liability=total_tax,
            estimated_monthly_tax=tax_res["estimated_monthly_tax"],
            annual_employee_pf=emp_pf,
            monthly_employee_pf=pf_res.monthly_employee_epf,
            annual_employer_contribution=pf_res.total_annual_employer_contribution,
            monthly_employer_contribution=pf_res.total_monthly_employer_contribution,
            annual_professional_tax=ann_pt,
            monthly_professional_tax=pt_res.monthly_pt,
            other_employee_deductions=other_ded,
            estimated_annual_take_home=take_home_annual,
            estimated_monthly_take_home=take_home_monthly,
            assumptions=assumptions,
            line_items=line_items,
            trace_steps=trace_steps,
            tax_rule_version_code=tax_rules.rule_version_code,
            pf_rule_version_code=pf_rules.rule_version_code,
            pt_rule_version_code=pt_rules.rule_version_code,
            input_hash=input_hash,
            result_hash=result_hash,
            rule_set_hash=combined_rule_hash,
        )

        # 9. Persistence to Database
        if persist:
            self.calc_repo.save_verified_calculation(verified_result, employee_id=employee_id)

        return verified_result

    def compare_regimes(
        self,
        salary_input: SalaryInput,
        state_code: str,
        age: int = 25,
        persist: bool = False,
    ) -> RegimeComparisonResult:
        old_res = self.calculate_salary(
            salary_input, regime=TaxRegime.OLD, state_code=state_code, age=age, persist=persist
        )
        new_res = self.calculate_salary(
            salary_input, regime=TaxRegime.NEW, state_code=state_code, age=age, persist=persist
        )

        diff = abs(old_res.total_annual_tax_liability - new_res.total_annual_tax_liability)
        if new_res.total_annual_tax_liability < old_res.total_annual_tax_liability:
            rec = TaxRegime.NEW
            note = f"New Tax Regime results in lower estimated tax liability by ₹{diff:,.2f} based on the supplied profile."
        elif old_res.total_annual_tax_liability < new_res.total_annual_tax_liability:
            rec = TaxRegime.OLD
            note = f"Old Tax Regime results in lower estimated tax liability by ₹{diff:,.2f} based on the claimed Chapter VI-A deductions."
        else:
            rec = TaxRegime.NEW
            note = "Both regimes produce identical estimated tax liability for this income profile."

        return RegimeComparisonResult(
            financial_year=salary_input.financial_year,
            old_regime=old_res,
            new_regime=new_res,
            tax_difference=diff,
            recommended_regime=rec,
            recommendation_note=note,
        )

    def get_calculation_by_id(self, calculation_id: int):
        import json

        calc_data = self.calc_repo.get_calculation_by_id(calculation_id)
        if not calc_data:
            return None
        snap = calc_data["result_snapshot"]
        if isinstance(snap, str):
            snap = json.loads(snap)
        inp = SalaryInput(
            financial_year=snap.get("financial_year", "2025-26"),
            annual_gross=Decimal(str(snap.get("annual_gross_salary", "1200000.00"))),
        )
        regime = TaxRegime(snap.get("regime", "NEW"))
        res = self.calculate_salary(
            salary_input=inp,
            regime=regime,
            state_code=snap.get("state_code", "KA"),
            persist=False,
        )
        return {"result": res}
