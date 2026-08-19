from dataclasses import dataclass
from decimal import Decimal

from app.engine.analytics.forecasting_engine import FinancialDataStatus


@dataclass(frozen=True)
class RaiseScenarioDTO:
    increment_pct: Decimal  # e.g., Decimal("0.10") for 10%
    new_annual_gross: Decimal
    gross_increase: Decimal
    new_annual_tax: Decimal
    tax_increase: Decimal
    new_annual_take_home: Decimal
    net_take_home_increase: Decimal
    marginal_retention_pct: Decimal  # Net Increase / Gross Increase * 100
    effective_tax_rate_pct: Decimal
    data_status: FinancialDataStatus = FinancialDataStatus.SIMULATED


@dataclass(frozen=True)
class BonusScenarioDTO:
    bonus_amount: Decimal
    current_annual_gross: Decimal
    new_annual_gross: Decimal
    projected_additional_tax: Decimal
    projected_additional_take_home: Decimal
    marginal_tax_rate_pct: Decimal
    data_status: FinancialDataStatus = FinancialDataStatus.SIMULATED


class FinancialSimulatorService:
    """
    Multi-Variable Financial Simulator Service.
    Enforces Rule 5: Bonus calculations evaluate annual gross increments; preserves 3-Tier TDS architecture.
    """

    @classmethod
    def simulate_raise(
        cls,
        current_annual_gross: Decimal,
        increment_pct: Decimal,
    ) -> RaiseScenarioDTO:
        new_gross = (current_annual_gross * (Decimal("1.00") + increment_pct)).quantize(Decimal("0.01"))
        gross_increase = new_gross - current_annual_gross

        # Tax calculation approximation (New Regime)
        def calc_tax(gross: Decimal) -> Decimal:
            if gross <= Decimal("700000.00"):
                return Decimal("0.00")  # Section 87A rebate
            taxable = gross - Decimal("75000.00")  # Standard deduction
            if taxable <= Decimal("300000.00"):
                return Decimal("0.00")
            elif taxable <= Decimal("700000.00"):
                return (taxable - Decimal("300000.00")) * Decimal("0.05")
            elif taxable <= Decimal("1000000.00"):
                return Decimal("20000.00") + (taxable - Decimal("700000.00")) * Decimal("0.10")
            elif taxable <= Decimal("1200000.00"):
                return Decimal("50000.00") + (taxable - Decimal("1000000.00")) * Decimal("0.15")
            elif taxable <= Decimal("1500000.00"):
                return Decimal("80000.00") + (taxable - Decimal("1200000.00")) * Decimal("0.20")
            else:
                return Decimal("140000.00") + (taxable - Decimal("1500000.00")) * Decimal("0.30")

        base_tax = calc_tax(current_annual_gross)
        new_tax = calc_tax(new_gross)
        tax_increase = new_tax - base_tax

        # Standard annual PF (capped) & PT
        annual_pf = min(current_annual_gross * Decimal("0.12"), Decimal("21600.00"))
        annual_pt = Decimal("2400.00")

        base_take_home = current_annual_gross - base_tax - annual_pf - annual_pt
        new_take_home = new_gross - new_tax - annual_pf - annual_pt
        net_increase = new_take_home - base_take_home

        retention_pct = (
            (net_increase / gross_increase * Decimal("100.00")).quantize(Decimal("0.01"))
            if gross_increase > 0
            else Decimal("0.00")
        )
        eff_tax_rate = (
            (new_tax / new_gross * Decimal("100.00")).quantize(Decimal("0.01")) if new_gross > 0 else Decimal("0.00")
        )

        return RaiseScenarioDTO(
            increment_pct=increment_pct,
            new_annual_gross=new_gross,
            gross_increase=gross_increase,
            new_annual_tax=new_tax.quantize(Decimal("0.01")),
            tax_increase=tax_increase.quantize(Decimal("0.01")),
            new_annual_take_home=new_take_home.quantize(Decimal("0.01")),
            net_take_home_increase=net_increase.quantize(Decimal("0.01")),
            marginal_retention_pct=retention_pct,
            effective_tax_rate_pct=eff_tax_rate,
            data_status=FinancialDataStatus.SIMULATED,
        )

    @classmethod
    def simulate_bonus(
        cls,
        current_annual_gross: Decimal,
        bonus_amount: Decimal,
    ) -> BonusScenarioDTO:
        new_gross = current_annual_gross + bonus_amount

        # Evaluate incremental annual liability
        def calc_tax(gross: Decimal) -> Decimal:
            if gross <= Decimal("700000.00"):
                return Decimal("0.00")
            taxable = gross - Decimal("75000.00")
            if taxable <= Decimal("1000000.00"):
                return (taxable - Decimal("300000.00")) * Decimal("0.10")
            elif taxable <= Decimal("1500000.00"):
                return Decimal("70000.00") + (taxable - Decimal("1000000.00")) * Decimal("0.20")
            else:
                return Decimal("170000.00") + (taxable - Decimal("1500000.00")) * Decimal("0.30")

        base_tax = calc_tax(current_annual_gross)
        new_tax = calc_tax(new_gross)
        additional_tax = (new_tax - base_tax).quantize(Decimal("0.01"))
        additional_take_home = (bonus_amount - additional_tax).quantize(Decimal("0.01"))

        marginal_rate = (
            (additional_tax / bonus_amount * Decimal("100.00")).quantize(Decimal("0.01"))
            if bonus_amount > 0
            else Decimal("0.00")
        )

        return BonusScenarioDTO(
            bonus_amount=bonus_amount,
            current_annual_gross=current_annual_gross,
            new_annual_gross=new_gross,
            projected_additional_tax=additional_tax,
            projected_additional_take_home=additional_take_home,
            marginal_tax_rate_pct=marginal_rate,
            data_status=FinancialDataStatus.SIMULATED,
        )
