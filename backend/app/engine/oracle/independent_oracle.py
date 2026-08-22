"""
SmartSalary India — Independent Regulatory Oracle Layer (Milestone M9.6)
Clean-room, zero-dependency validation oracle for statutory Indian taxation and compliance.
Calculates independent benchmark values without importing production engine code.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


def _quantize_inr(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class OracleSalaryInput:
    financial_year: str
    regime: str  # "NEW" or "OLD"
    state_code: str
    annual_gross: Decimal
    basic_percentage: Decimal = Decimal("0.50")
    custom_monthly_basic: Decimal | None = None
    section_80c: Decimal = Decimal("0.00")
    section_80d: Decimal = Decimal("0.00")


@dataclass(frozen=True)
class OracleCalculationResult:
    annual_gross: Decimal
    taxable_income: Decimal
    standard_deduction: Decimal
    slab_tax: Decimal
    section_87a_rebate: Decimal
    tax_after_rebate: Decimal
    cess: Decimal
    total_tax: Decimal
    annual_employee_pf: Decimal
    annual_employer_pf: Decimal
    annual_employer_eps: Decimal
    annual_employer_edli: Decimal
    annual_professional_tax: Decimal
    annual_take_home: Decimal
    monthly_take_home: Decimal
    total_employer_cost: Decimal


class IndependentRegulatoryOracle:
    """
    Independent Statutory Oracle.
    Contains clean-room formulas authored directly from primary acts (Income-tax Act, EPF Act, State PT Acts).
    Calculates expected values completely independent of production engine internals.
    """

    @classmethod
    def calculate_pt(cls, state_code: str, monthly_gross: Decimal, is_february: bool = False) -> Decimal:
        state = state_code.upper()
        if state == "KA":
            return Decimal("200.00") if monthly_gross >= Decimal("15000.00") else Decimal("0.00")
        elif state == "MH":
            if monthly_gross > Decimal("10000.00"):
                return Decimal("300.00") if is_february else Decimal("200.00")
            elif monthly_gross > Decimal("7500.00"):
                return Decimal("175.00")
            return Decimal("0.00")
        elif state == "TS":
            if monthly_gross > Decimal("20000.00"):
                return Decimal("200.00")
            elif monthly_gross > Decimal("15000.00"):
                return Decimal("150.00")
            return Decimal("0.00")
        elif state == "WB":
            if monthly_gross > Decimal("40000.00"):
                return Decimal("200.00")
            elif monthly_gross > Decimal("25000.00"):
                return Decimal("150.00")
            elif monthly_gross > Decimal("15000.00"):
                return Decimal("130.00")
            elif monthly_gross > Decimal("10000.00"):
                return Decimal("110.00")
            return Decimal("0.00")
        elif state == "GJ":
            if monthly_gross > Decimal("12000.00"):
                return Decimal("200.00")
            elif monthly_gross > Decimal("9000.00"):
                return Decimal("150.00")
            elif monthly_gross > Decimal("6000.00"):
                return Decimal("80.00")
            return Decimal("0.00")
        elif state == "TN":
            if monthly_gross >= Decimal("50000.00"):
                return Decimal("208.33")
            elif monthly_gross >= Decimal("25000.00"):
                return Decimal("104.17")
            return Decimal("0.00")
        return Decimal("0.00")

    @classmethod
    def calculate_annual_pt(cls, state_code: str, annual_gross: Decimal) -> Decimal:
        monthly_gross = annual_gross / Decimal("12")
        state = state_code.upper()
        if state == "KA":
            return Decimal("2400.00") if monthly_gross >= Decimal("15000.00") else Decimal("0.00")
        elif state == "MH":
            return (
                Decimal("2500.00")
                if monthly_gross > Decimal("10000.00")
                else (Decimal("2100.00") if monthly_gross > Decimal("7500.00") else Decimal("0.00"))
            )
        elif state == "TS":
            return (
                Decimal("2400.00")
                if monthly_gross > Decimal("20000.00")
                else (Decimal("1800.00") if monthly_gross > Decimal("15000.00") else Decimal("0.00"))
            )
        elif state == "WB":
            return cls.calculate_pt("WB", monthly_gross) * Decimal("12")
        elif state == "GJ":
            return cls.calculate_pt("GJ", monthly_gross) * Decimal("12")
        elif state == "TN":
            return Decimal("2500.00") if annual_gross >= Decimal("600000.00") else Decimal("1250.00")
        return Decimal("0.00")

    @classmethod
    def _compute_surcharge(cls, taxable: Decimal, tax_after_rebate: Decimal, is_old_regime: bool = False) -> tuple[Decimal, Decimal]:
        if tax_after_rebate <= Decimal("0.00") or taxable <= Decimal("5000000.00"):
            return Decimal("0.00"), Decimal("0.00")

        if taxable > Decimal("20000000.00"):
            rate = Decimal("0.25")
            threshold = Decimal("20000000.00")
        elif taxable > Decimal("10000000.00"):
            rate = Decimal("0.15")
            threshold = Decimal("10000000.00")
        else:
            rate = Decimal("0.10")
            threshold = Decimal("5000000.00")

        surcharge = _quantize_inr(tax_after_rebate * rate)

        # Marginal relief on surcharge:
        # Find applicable surcharge rate on threshold T (previous tier rate)
        if threshold >= Decimal("50000000.00"):
            prev_surcharge_rate = Decimal("0.25")
        elif threshold >= Decimal("20000000.00"):
            prev_surcharge_rate = Decimal("0.15")
        elif threshold >= Decimal("10000000.00"):
            prev_surcharge_rate = Decimal("0.10")
        else:
            prev_surcharge_rate = Decimal("0.00")

        excess_income = taxable - threshold
        tax_on_threshold = max(Decimal("0.00"), tax_after_rebate - _quantize_inr(excess_income * Decimal("0.30")))
        surcharge_on_threshold = _quantize_inr(tax_on_threshold * prev_surcharge_rate)
        max_allowed_total = tax_on_threshold + surcharge_on_threshold + excess_income

        if (tax_after_rebate + surcharge) > max_allowed_total:
            marginal_relief = (tax_after_rebate + surcharge) - max_allowed_total
            surcharge = max(Decimal("0.00"), surcharge - marginal_relief)
        else:
            marginal_relief = Decimal("0.00")

        return surcharge, marginal_relief

    @classmethod
    def calculate_fy2025_26_new(cls, gross: Decimal, state: str) -> OracleCalculationResult:
        std_ded = min(gross, Decimal("75000.00"))
        taxable = max(Decimal("0.00"), gross - std_ded)

        # Slabs under FY 2025-26 New Regime: 0-4L 0%, 4-8L 5%, 8-12L 10%, 12-16L 15%, 16-20L 20%, 20-24L 25%, >24L 30%
        slab_tax = Decimal("0.00")
        if taxable > Decimal("2400000.00"):
            slab_tax += (taxable - Decimal("2400000.00")) * Decimal("0.30")
            slab_tax += Decimal("100000.00")  # 20-24L @ 25%
            slab_tax += Decimal("80000.00")  # 16-20L @ 20%
            slab_tax += Decimal("60000.00")  # 12-16L @ 15%
            slab_tax += Decimal("40000.00")  # 8-12L @ 10%
            slab_tax += Decimal("20000.00")  # 4-8L @ 5%
        elif taxable > Decimal("2000000.00"):
            slab_tax += (taxable - Decimal("2000000.00")) * Decimal("0.25")
            slab_tax += Decimal("80000.00")  # 16-20L @ 20%
            slab_tax += Decimal("60000.00")  # 12-16L @ 15%
            slab_tax += Decimal("40000.00")  # 8-12L @ 10%
            slab_tax += Decimal("20000.00")  # 4-8L @ 5%
        elif taxable > Decimal("1600000.00"):
            slab_tax += (taxable - Decimal("1600000.00")) * Decimal("0.20")
            slab_tax += Decimal("60000.00")  # 12-16L @ 15%
            slab_tax += Decimal("40000.00")  # 8-12L @ 10%
            slab_tax += Decimal("20000.00")  # 4-8L @ 5%
        elif taxable > Decimal("1200000.00"):
            slab_tax += (taxable - Decimal("1200000.00")) * Decimal("0.15")
            slab_tax += Decimal("40000.00")  # 8-12L @ 10%
            slab_tax += Decimal("20000.00")  # 4-8L @ 5%
        elif taxable > Decimal("800000.00"):
            slab_tax += (taxable - Decimal("800000.00")) * Decimal("0.10")
            slab_tax += Decimal("20000.00")  # 4-8L @ 5%
        elif taxable > Decimal("400000.00"):
            slab_tax += (taxable - Decimal("400000.00")) * Decimal("0.05")

        # Rebate under Section 87A: Taxable <= 12,00,000 -> full rebate (max ₹60,000)
        if taxable <= Decimal("1200000.00"):
            rebate = slab_tax
            marginal_relief_87a = Decimal("0.00")
        else:
            rebate = Decimal("0.00")
            # Section 87A Marginal Relief under Section 115BAC
            excess_income = taxable - Decimal("1200000.00")
            if slab_tax > excess_income:
                marginal_relief_87a = slab_tax - excess_income
            else:
                marginal_relief_87a = Decimal("0.00")

        tax_after_rebate = max(Decimal("0.00"), slab_tax - rebate - marginal_relief_87a)
        surcharge, _ = cls._compute_surcharge(taxable, tax_after_rebate, is_old_regime=False)
        cess = _quantize_inr((tax_after_rebate + surcharge) * Decimal("0.04"))
        unrounded_total_tax = tax_after_rebate + surcharge + cess

        # Round to nearest 10 (Section 288B)
        remainder = unrounded_total_tax % Decimal("10")
        if remainder >= Decimal("5"):
            total_tax = unrounded_total_tax + (Decimal("10") - remainder)
        else:
            total_tax = unrounded_total_tax - remainder
        total_tax = _quantize_inr(total_tax)

        # EPF: 12% of basic (capped at 15k/mo)
        monthly_basic = min(gross / Decimal("12") * Decimal("0.50"), Decimal("15000.00"))
        annual_emp_pf = _quantize_inr(monthly_basic * Decimal("0.12") * Decimal("12"))
        annual_empr_pf = _quantize_inr(monthly_basic * Decimal("0.0367") * Decimal("12"))
        annual_empr_eps = _quantize_inr(monthly_basic * Decimal("0.0833") * Decimal("12"))
        annual_empr_edli = _quantize_inr(monthly_basic * Decimal("0.005") * Decimal("12"))

        pt_annual = cls.calculate_annual_pt(state, gross)

        take_home = gross - total_tax - annual_emp_pf - pt_annual
        monthly_take_home = _quantize_inr(take_home / Decimal("12"))
        total_cost = gross + annual_empr_pf + annual_empr_eps + annual_empr_edli

        return OracleCalculationResult(
            annual_gross=gross,
            taxable_income=taxable,
            standard_deduction=std_ded,
            slab_tax=slab_tax,
            section_87a_rebate=rebate,
            tax_after_rebate=tax_after_rebate,
            cess=cess,
            total_tax=total_tax,
            annual_employee_pf=annual_emp_pf,
            annual_employer_pf=annual_empr_pf,
            annual_employer_eps=annual_empr_eps,
            annual_employer_edli=annual_empr_edli,
            annual_professional_tax=pt_annual,
            annual_take_home=take_home,
            monthly_take_home=monthly_take_home,
            total_employer_cost=total_cost,
        )

    @classmethod
    def calculate_fy2026_27_new(cls, gross: Decimal, state: str) -> OracleCalculationResult:
        return cls.calculate_fy2025_26_new(gross, state)

    @classmethod
    def calculate_fy2024_25_new(cls, gross: Decimal, state: str) -> OracleCalculationResult:
        std_ded = min(gross, Decimal("75000.00"))
        taxable = max(Decimal("0.00"), gross - std_ded)

        # Slabs 24-25: 0-3L(0%), 3-7L(5%), 7-10L(10%), 10-12L(15%), 12-15L(20%), >15L(30%)
        slab_tax = Decimal("0.00")
        if taxable > Decimal("1500000.00"):
            slab_tax += (taxable - Decimal("1500000.00")) * Decimal("0.30")
            slab_tax += Decimal("60000.00")  # 12-15L @ 20%
            slab_tax += Decimal("30000.00")  # 10-12L @ 15%
            slab_tax += Decimal("30000.00")  # 7-10L @ 10%
            slab_tax += Decimal("20000.00")  # 3-7L @ 5%
        elif taxable > Decimal("1200000.00"):
            slab_tax += (taxable - Decimal("1200000.00")) * Decimal("0.20")
            slab_tax += Decimal("30000.00")  # 10-12L @ 15%
            slab_tax += Decimal("30000.00")  # 7-10L @ 10%
            slab_tax += Decimal("20000.00")  # 3-7L @ 5%
        elif taxable > Decimal("1000000.00"):
            slab_tax += (taxable - Decimal("1000000.00")) * Decimal("0.15")
            slab_tax += Decimal("30000.00")  # 7-10L @ 10%
            slab_tax += Decimal("20000.00")  # 3-7L @ 5%
        elif taxable > Decimal("700000.00"):
            slab_tax += (taxable - Decimal("700000.00")) * Decimal("0.10")
            slab_tax += Decimal("20000.00")  # 3-7L @ 5%
        elif taxable > Decimal("300000.00"):
            slab_tax += (taxable - Decimal("300000.00")) * Decimal("0.05")

        # Rebate under Section 87A (FY 2024-25 New Regime): Taxable <= 7,00,000 -> full rebate (max 25k)
        if taxable <= Decimal("700000.00"):
            rebate = slab_tax
            marginal_relief_87a = Decimal("0.00")
        else:
            rebate = Decimal("0.00")
            excess_income = taxable - Decimal("700000.00")
            if slab_tax > excess_income:
                marginal_relief_87a = slab_tax - excess_income
            else:
                marginal_relief_87a = Decimal("0.00")

        tax_after_rebate = max(Decimal("0.00"), slab_tax - rebate - marginal_relief_87a)
        surcharge, _ = cls._compute_surcharge(taxable, tax_after_rebate, is_old_regime=False)
        cess = _quantize_inr((tax_after_rebate + surcharge) * Decimal("0.04"))
        unrounded_total_tax = tax_after_rebate + surcharge + cess
        remainder = unrounded_total_tax % Decimal("10")
        if remainder >= Decimal("5"):
            total_tax = unrounded_total_tax + (Decimal("10") - remainder)
        else:
            total_tax = unrounded_total_tax - remainder
        total_tax = _quantize_inr(total_tax)

        monthly_basic = min(gross / Decimal("12") * Decimal("0.50"), Decimal("15000.00"))
        annual_emp_pf = _quantize_inr(monthly_basic * Decimal("0.12") * Decimal("12"))
        annual_empr_pf = _quantize_inr(monthly_basic * Decimal("0.0367") * Decimal("12"))
        annual_empr_eps = _quantize_inr(monthly_basic * Decimal("0.0833") * Decimal("12"))
        annual_empr_edli = _quantize_inr(monthly_basic * Decimal("0.005") * Decimal("12"))

        pt_annual = cls.calculate_annual_pt(state, gross)

        take_home = gross - total_tax - annual_emp_pf - pt_annual
        monthly_take_home = _quantize_inr(take_home / Decimal("12"))
        total_cost = gross + annual_empr_pf + annual_empr_eps + annual_empr_edli

        return OracleCalculationResult(
            annual_gross=gross,
            taxable_income=taxable,
            standard_deduction=std_ded,
            slab_tax=slab_tax,
            section_87a_rebate=rebate,
            tax_after_rebate=tax_after_rebate,
            cess=cess,
            total_tax=total_tax,
            annual_employee_pf=annual_emp_pf,
            annual_employer_pf=annual_empr_pf,
            annual_employer_eps=annual_empr_eps,
            annual_employer_edli=annual_empr_edli,
            annual_professional_tax=pt_annual,
            annual_take_home=take_home,
            monthly_take_home=monthly_take_home,
            total_employer_cost=total_cost,
        )

    @classmethod
    def calculate_fy2025_26_old(
        cls, gross: Decimal, state: str, sec_80c: Decimal = Decimal("0.00"), sec_80d: Decimal = Decimal("0.00")
    ) -> OracleCalculationResult:
        std_ded = min(gross, Decimal("50000.00"))
        claimed_80c = min(sec_80c, Decimal("150000.00"))
        claimed_80d = min(sec_80d, Decimal("25000.00"))
        total_ded = std_ded + claimed_80c + claimed_80d
        taxable = max(Decimal("0.00"), gross - total_ded)

        # Old Regime Slabs: 0-2.5L 0%, 2.5-5L 5%, 5-10L 20%, >10L 30%
        slab_tax = Decimal("0.00")
        if taxable > Decimal("1000000.00"):
            slab_tax += (taxable - Decimal("1000000.00")) * Decimal("0.30")
            slab_tax += Decimal("100000.00")  # 5-10L @ 20%
            slab_tax += Decimal("12500.00")  # 2.5-5L @ 5%
        elif taxable > Decimal("500000.00"):
            slab_tax += (taxable - Decimal("500000.00")) * Decimal("0.20")
            slab_tax += Decimal("12500.00")
        elif taxable > Decimal("250000.00"):
            slab_tax += (taxable - Decimal("250000.00")) * Decimal("0.05")

        # Rebate under Section 87A (Old Regime): Taxable <= 5,00,000 -> max ₹12,500
        if taxable <= Decimal("500000.00"):
            rebate = min(slab_tax, Decimal("12500.00"))
            marginal_relief_87a = Decimal("0.00")
        else:
            rebate = Decimal("0.00")
            excess_income = taxable - Decimal("500000.00")
            if slab_tax > excess_income:
                marginal_relief_87a = slab_tax - excess_income
            else:
                marginal_relief_87a = Decimal("0.00")

        tax_after_rebate = max(Decimal("0.00"), slab_tax - rebate - marginal_relief_87a)
        surcharge, _ = cls._compute_surcharge(taxable, tax_after_rebate, is_old_regime=True)
        cess = _quantize_inr((tax_after_rebate + surcharge) * Decimal("0.04"))
        unrounded_total_tax = tax_after_rebate + surcharge + cess
        remainder = unrounded_total_tax % Decimal("10")
        if remainder >= Decimal("5"):
            total_tax = unrounded_total_tax + (Decimal("10") - remainder)
        else:
            total_tax = unrounded_total_tax - remainder
        total_tax = _quantize_inr(total_tax)

        monthly_basic = min(gross / Decimal("12") * Decimal("0.50"), Decimal("15000.00"))
        annual_emp_pf = _quantize_inr(monthly_basic * Decimal("0.12") * Decimal("12"))
        annual_empr_pf = _quantize_inr(monthly_basic * Decimal("0.0367") * Decimal("12"))
        annual_empr_eps = _quantize_inr(monthly_basic * Decimal("0.0833") * Decimal("12"))
        annual_empr_edli = _quantize_inr(monthly_basic * Decimal("0.005") * Decimal("12"))

        pt_annual = cls.calculate_annual_pt(state, gross)

        take_home = gross - total_tax - annual_emp_pf - pt_annual
        monthly_take_home = _quantize_inr(take_home / Decimal("12"))
        total_cost = gross + annual_empr_pf + annual_empr_eps + annual_empr_edli

        return OracleCalculationResult(
            annual_gross=gross,
            taxable_income=taxable,
            standard_deduction=std_ded,
            slab_tax=slab_tax,
            section_87a_rebate=rebate,
            tax_after_rebate=tax_after_rebate,
            cess=cess,
            total_tax=total_tax,
            annual_employee_pf=annual_emp_pf,
            annual_employer_pf=annual_empr_pf,
            annual_employer_eps=annual_empr_eps,
            annual_employer_edli=annual_empr_edli,
            annual_professional_tax=pt_annual,
            annual_take_home=take_home,
            monthly_take_home=monthly_take_home,
            total_employer_cost=total_cost,
        )
