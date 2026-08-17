from decimal import Decimal

from app.engine.common.money import quantize_currency
from app.engine.dto.pf_dto import PfCalculationInput, PfCalculationResult, PfRuleSet


class PfCalculator:
    """
    Pure Zero-I/O Provident Fund Engine.
    Evaluates:
    - Applicability & wage base (Basic + DA)
    - Statutory Wage Ceiling (₹15,000 / month) or voluntary higher wage opt-in
    - Employee EPF (12% of applicable wage base)
    - Employer EPF (3.67%), Employer EPS (8.33% capped at ₹15,000 ceiling: max ₹1,250/mo), EDLI (0.50% capped: max ₹75/mo).
    """

    @classmethod
    def calculate_pf(
        cls,
        inp: PfCalculationInput,
        rules: PfRuleSet,
    ) -> PfCalculationResult:
        if not inp.is_pf_applicable or inp.pf_wage_base_monthly <= Decimal("0.00"):
            zero = Decimal("0.00")
            return PfCalculationResult(
                monthly_employee_epf=zero,
                annual_employee_epf=zero,
                monthly_employer_epf=zero,
                annual_employer_epf=zero,
                monthly_employer_eps=zero,
                annual_employer_eps=zero,
                monthly_employer_edli=zero,
                annual_employer_edli=zero,
                total_monthly_employer_contribution=zero,
                total_annual_employer_contribution=zero,
                rule_version_code=rules.rule_version_code,
            )

        wage_base = inp.pf_wage_base_monthly
        ceiling = rules.statutory_wage_ceiling

        # 1. Employee EPF Base
        if inp.opt_in_higher_wage:
            employee_wage_base = wage_base
        else:
            employee_wage_base = min(wage_base, ceiling)

        monthly_employee_epf = quantize_currency(employee_wage_base * rules.employee_epf_rate)
        annual_employee_epf = quantize_currency(monthly_employee_epf * Decimal("12"))

        # 2. Employer EPS (strictly capped at statutory wage ceiling ₹15,000 -> max ₹1,250)
        eps_base = min(wage_base, rules.eps_wage_ceiling)
        monthly_employer_eps = quantize_currency(eps_base * rules.employer_eps_rate)

        # 3. Employer EPF (Balance of 12% total employer contribution minus EPS)
        # Total 12% contribution on applicable wage base
        total_employer_12pct = quantize_currency(employee_wage_base * rules.employee_epf_rate)
        monthly_employer_epf = max(Decimal("0.00"), total_employer_12pct - monthly_employer_eps)

        # 4. Employer EDLI (capped at ₹15,000 ceiling -> max ₹75)
        monthly_employer_edli = quantize_currency(eps_base * rules.employer_edli_rate)

        annual_employer_epf = quantize_currency(monthly_employer_epf * Decimal("12"))
        annual_employer_eps = quantize_currency(monthly_employer_eps * Decimal("12"))
        annual_employer_edli = quantize_currency(monthly_employer_edli * Decimal("12"))

        total_monthly_employer = monthly_employer_epf + monthly_employer_eps + monthly_employer_edli
        total_annual_employer = annual_employer_epf + annual_employer_eps + annual_employer_edli

        return PfCalculationResult(
            monthly_employee_epf=monthly_employee_epf,
            annual_employee_epf=annual_employee_epf,
            monthly_employer_epf=monthly_employer_epf,
            annual_employer_epf=annual_employer_epf,
            monthly_employer_eps=monthly_employer_eps,
            annual_employer_eps=annual_employer_eps,
            monthly_employer_edli=monthly_employer_edli,
            annual_employer_edli=annual_employer_edli,
            total_monthly_employer_contribution=total_monthly_employer,
            total_annual_employer_contribution=total_annual_employer,
            rule_version_code=rules.rule_version_code,
        )
