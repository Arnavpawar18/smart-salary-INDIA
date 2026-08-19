from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.engine.common.enums import TaxRegime
from app.engine.common.money import quantize_currency
from app.engine.dto.result_dto import VerifiedCalculationResult
from app.engine.dto.salary_dto import SalaryInput
from app.services.calculation_service import CalculationService
from app.services.salary_service import SalaryService


class ScenarioService:
    """
    Orchestrates What-If raises, multi-scenario comparisons, and 'What Changed?' deltas.
    Consumes the frozen Phase 2 CalculationService; never computes tax/PF/PT math directly.
    """

    MAX_SCENARIOS_PER_REQUEST = 3

    def __init__(self, db: Session):
        self.calc_service = CalculationService(db)

    def calculate_what_if_raises(
        self,
        base_salary: Decimal,
        financial_year: str,
        state_code: str,
        regime: TaxRegime,
        raise_percentages: list[Decimal] = [Decimal("5"), Decimal("10"), Decimal("20")],
    ) -> dict[str, Any]:
        base_inp = SalaryInput(financial_year=financial_year, annual_gross=base_salary)
        base_res = self.calc_service.calculate_salary(base_inp, regime=regime, state_code=state_code, persist=False)

        simulations = []
        for pct in raise_percentages[: self.MAX_SCENARIOS_PER_REQUEST]:
            multiplier = Decimal("1.00") + (pct / Decimal("100"))
            sim_gross = quantize_currency(base_salary * multiplier)
            gross_delta = sim_gross - base_salary

            sim_inp = SalaryInput(financial_year=financial_year, annual_gross=sim_gross)
            sim_res = self.calc_service.calculate_salary(sim_inp, regime=regime, state_code=state_code, persist=False)
            sim_metrics = SalaryService.compute_analytical_metrics(sim_res)

            tax_delta = sim_res.total_annual_tax_liability - base_res.total_annual_tax_liability
            take_home_delta = sim_res.estimated_annual_take_home - base_res.estimated_annual_take_home
            marginal_retention_rate = (
                (take_home_delta / gross_delta * Decimal("100")) if gross_delta > 0 else Decimal("0.00")
            )

            simulations.append(
                {
                    "percentage_increase": f"{pct}%",
                    "simulated_gross": sim_gross,
                    "gross_delta": gross_delta,
                    "simulated_tax": sim_res.total_annual_tax_liability,
                    "tax_delta": tax_delta,
                    "simulated_take_home": sim_res.estimated_annual_take_home,
                    "take_home_delta": take_home_delta,
                    "marginal_retention_rate": quantize_currency(marginal_retention_rate),
                    "retention_explanation": f"You keep approximately ₹{take_home_delta:,.2f} of this ₹{gross_delta:,.2f} raise ({quantize_currency(marginal_retention_rate)}% retention).",
                    "effective_take_home_rate": sim_metrics["effective_take_home_rate"],
                }
            )

        return {
            "base_gross": base_salary,
            "base_tax": base_res.total_annual_tax_liability,
            "base_take_home": base_res.estimated_annual_take_home,
            "simulations": simulations,
        }

    def compute_what_changed_delta(
        self,
        res_before: VerifiedCalculationResult,
        res_after: VerifiedCalculationResult,
    ) -> dict[str, Any]:
        """Explains deterministic changes between two calculation runs."""
        gross_delta = res_after.annual_gross_salary - res_before.annual_gross_salary
        taxable_delta = res_after.taxable_income - res_before.taxable_income
        tax_delta = res_after.total_annual_tax_liability - res_before.total_annual_tax_liability
        pf_delta = res_after.annual_employee_pf - res_before.annual_employee_pf
        pt_delta = res_after.annual_professional_tax - res_before.annual_professional_tax
        take_home_delta = res_after.estimated_annual_take_home - res_before.estimated_annual_take_home

        narrative_items = []
        if gross_delta > 0:
            narrative_items.append(f"Annual Gross salary increased by ₹{gross_delta:,.2f}.")
        elif gross_delta < 0:
            narrative_items.append(f"Annual Gross salary decreased by ₹{abs(gross_delta):,.2f}.")

        if taxable_delta > 0:
            narrative_items.append(f"Taxable Income increased by ₹{taxable_delta:,.2f}.")
        elif taxable_delta < 0:
            narrative_items.append(f"Taxable Income decreased by ₹{abs(taxable_delta):,.2f}.")

        if tax_delta > 0:
            narrative_items.append(
                f"Income Tax liability increased by ₹{tax_delta:,.2f} due to progressive slab brackets."
            )
        elif tax_delta < 0:
            narrative_items.append(f"Income Tax liability decreased by ₹{abs(tax_delta):,.2f}.")

        if take_home_delta > 0:
            narrative_items.append(f"Net annual take-home increased by ₹{take_home_delta:,.2f}.")
        elif take_home_delta < 0:
            narrative_items.append(f"Net annual take-home decreased by ₹{abs(take_home_delta):,.2f}.")

        return {
            "gross_delta": gross_delta,
            "taxable_delta": taxable_delta,
            "tax_delta": tax_delta,
            "pf_delta": pf_delta,
            "pt_delta": pt_delta,
            "take_home_delta": take_home_delta,
            "narrative": narrative_items,
        }
