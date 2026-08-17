from decimal import Decimal
from typing import Dict, Optional, Tuple

from app.engine.common.money import quantize_currency
from app.engine.common.rounding import DEFAULT_ROUNDING_POLICY
from app.engine.dto.tax_dto import TaxCalculationInput, TaxRuleSet
from app.engine.tax.cess import CessCalculator
from app.engine.tax.marginal_relief import MarginalReliefCalculator
from app.engine.tax.rebates import RebateCalculator
from app.engine.tax.slabs import SlabCalculator
from app.engine.tax.surcharge import SurchargeCalculator


class TaxCalculator:
    """
    Pure Zero-I/O Income Tax Engine.
    Executes the statutory pipeline:
    Gross Salary -> Standard Deduction & Section 80 Deductions -> Taxable Income
    -> Slabs -> Section 87A Rebate -> Rebate Marginal Relief -> Surcharge
    -> Surcharge Relief -> Health & Education Cess -> Total Tax Liability.
    """

    @classmethod
    def calculate_tax(
        cls,
        inp: TaxCalculationInput,
        rules: TaxRuleSet,
    ) -> Dict[str, Decimal]:
        gross_salary = quantize_currency(inp.annual_gross_salary)

        # 1. Deductions
        # Standard deduction
        std_ded_rule = next((d for d in rules.deductions if d.is_standard_deduction), None)
        std_ded_limit = std_ded_rule.max_limit if std_ded_rule and std_ded_rule.max_limit else Decimal("0.00")
        if inp.standard_deduction_override is not None:
            standard_deduction = min(gross_salary, inp.standard_deduction_override)
        else:
            standard_deduction = min(gross_salary, std_ded_limit)

        # Chapter VI-A deductions (Section 80C, 80D, etc. - applicable primarily in OLD regime)
        sec_80c_rule = next((d for d in rules.deductions if "80C" in d.deduction_code), None)
        max_80c = sec_80c_rule.max_limit if sec_80c_rule and sec_80c_rule.max_limit else Decimal("0.00")
        claimed_80c = min(inp.section_80c, max_80c)

        sec_80d_rule = next((d for d in rules.deductions if "80D" in d.deduction_code), None)
        max_80d = sec_80d_rule.max_limit if sec_80d_rule and sec_80d_rule.max_limit else Decimal("0.00")
        claimed_80d = min(inp.section_80d, max_80d)

        total_deductions = standard_deduction + claimed_80c + claimed_80d + inp.other_deductions + inp.other_exemptions
        taxable_income = max(Decimal("0.00"), gross_salary - total_deductions)

        # 2. Slab Tax
        slab_tax, slab_breakdowns = SlabCalculator.calculate_slab_tax(taxable_income, rules.slabs)

        # 3. Rebate Section 87A
        rebate = RebateCalculator.calculate_rebate(taxable_income, slab_tax, rules.rebates)
        rebate_marginal_relief = Decimal("0.00")
        if rebate == Decimal("0.00"):
            rebate_marginal_relief = MarginalReliefCalculator.calculate_rebate_marginal_relief(
                taxable_income, slab_tax, rules.rebates
            )

        tax_after_rebate = max(Decimal("0.00"), slab_tax - rebate - rebate_marginal_relief)

        # 4. Surcharge & Surcharge Marginal Relief
        surcharge = SurchargeCalculator.calculate_surcharge(taxable_income, tax_after_rebate, rules.surcharges)
        surcharge_marginal_relief = MarginalReliefCalculator.calculate_surcharge_marginal_relief(
            taxable_income, tax_after_rebate, surcharge, rules.surcharges
        )
        tax_and_surcharge = tax_after_rebate + surcharge - surcharge_marginal_relief

        # 5. Health & Education Cess (4%)
        cess = CessCalculator.calculate_cess(tax_and_surcharge, rules.cess_rules)

        # 6. Total Annual Tax Liability (Statutory Section 288B round to nearest ₹10)
        unrounded_total_tax = tax_and_surcharge + cess
        total_tax = DEFAULT_ROUNDING_POLICY.round_to_nearest_ten(unrounded_total_tax)

        estimated_monthly_tax = quantize_currency(total_tax / Decimal("12"))

        return {
            "annual_gross_salary": gross_salary,
            "standard_deduction": standard_deduction,
            "claimed_80c": claimed_80c,
            "claimed_80d": claimed_80d,
            "total_deductions": total_deductions,
            "taxable_income": taxable_income,
            "slab_tax": slab_tax,
            "section_87a_rebate": rebate,
            "rebate_marginal_relief": rebate_marginal_relief,
            "tax_after_rebate": tax_after_rebate,
            "surcharge": surcharge,
            "surcharge_marginal_relief": surcharge_marginal_relief,
            "health_education_cess": cess,
            "total_annual_tax_liability": total_tax,
            "estimated_monthly_tax": estimated_monthly_tax,
        }
