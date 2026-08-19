from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class FinancialDataStatus(StrEnum):
    ACTUAL = "ACTUAL"
    CALCULATED = "CALCULATED"
    PROJECTED = "PROJECTED"
    SIMULATED = "SIMULATED"
    FORECAST = "FORECAST"
    ESTIMATED = "ESTIMATED"


@dataclass(frozen=True)
class ForecastPeriodDTO:
    month_offset: int  # 1 to 12
    period_code: str  # e.g., '2026-05'
    projected_monthly_gross: Decimal
    projected_monthly_pf: Decimal
    projected_monthly_pt: Decimal
    projected_monthly_tds: Decimal
    projected_monthly_take_home: Decimal
    data_status: FinancialDataStatus = FinancialDataStatus.PROJECTED


@dataclass(frozen=True)
class SalaryForecastDTO:
    employee_id: int
    current_annual_gross: Decimal
    projected_annual_gross: Decimal
    projected_annual_tax: Decimal
    projected_annual_pf: Decimal
    projected_annual_pt: Decimal
    projected_annual_take_home: Decimal
    effective_tax_rate_pct: Decimal
    monthly_schedule: list[ForecastPeriodDTO]
    data_status: FinancialDataStatus = FinancialDataStatus.PROJECTED


class SalaryForecastEngine:
    """
    Deterministic Salary & Tax Forecasting Engine.
    Produces 3-Month, 6-Month, 12-Month forward financial schedules.
    Enforces Rule: Forecasting must NEVER be presented as actual financial data (Status = PROJECTED).
    """

    @classmethod
    def generate_forecast(
        cls,
        employee_id: int,
        current_monthly_gross: Decimal,
        annual_increment_pct: Decimal = Decimal("0.00"),  # e.g. 0.10 for 10%
        increment_start_month: int = 4,  # e.g. Month 4 (July)
        current_year: int = 2026,
        current_month: int = 4,
    ) -> SalaryForecastDTO:
        monthly_schedule: list[ForecastPeriodDTO] = []

        annual_gross = Decimal("0.00")
        annual_pf = Decimal("0.00")
        annual_pt = Decimal("0.00")
        annual_tds = Decimal("0.00")
        annual_take_home = Decimal("0.00")

        for i in range(1, 13):
            # Calculate target month and year
            m = ((current_month + i - 2) % 12) + 1
            y = current_year + ((current_month + i - 1) // 12)
            period_code = f"{y}-{m:02d}"

            # Apply increment if offset reached
            if i >= increment_start_month and annual_increment_pct > Decimal("0.00"):
                m_gross = (current_monthly_gross * (Decimal("1.00") + annual_increment_pct)).quantize(Decimal("0.01"))
            else:
                m_gross = current_monthly_gross.quantize(Decimal("0.01"))

            # Deterministic statutory estimates
            m_pf = min(m_gross * Decimal("0.12"), Decimal("1800.00")).quantize(Decimal("0.01"))
            m_pt = Decimal("200.00") if m_gross > Decimal("15000.00") else Decimal("0.00")

            # Projected TDS estimation (New Regime progressive bracket approximation)
            ann_equiv = m_gross * Decimal("12.00")
            if ann_equiv <= Decimal("700000.00"):
                m_tds = Decimal("0.00")  # Section 87A rebate
            else:
                m_tds = ((ann_equiv - Decimal("300000.00")) * Decimal("0.10") / Decimal("12.00")).quantize(
                    Decimal("0.01")
                )

            m_take_home = m_gross - m_pf - m_pt - m_tds

            annual_gross += m_gross
            annual_pf += m_pf
            annual_pt += m_pt
            annual_tds += m_tds
            annual_take_home += m_take_home

            monthly_schedule.append(
                ForecastPeriodDTO(
                    month_offset=i,
                    period_code=period_code,
                    projected_monthly_gross=m_gross,
                    projected_monthly_pf=m_pf,
                    projected_monthly_pt=m_pt,
                    projected_monthly_tds=m_tds,
                    projected_monthly_take_home=m_take_home,
                    data_status=FinancialDataStatus.PROJECTED,
                )
            )

        eff_rate = (
            (annual_tds / annual_gross * Decimal("100.00")).quantize(Decimal("0.01"))
            if annual_gross > 0
            else Decimal("0.00")
        )

        return SalaryForecastDTO(
            employee_id=employee_id,
            current_annual_gross=current_monthly_gross * Decimal("12.00"),
            projected_annual_gross=annual_gross,
            projected_annual_tax=annual_tds,
            projected_annual_pf=annual_pf,
            projected_annual_pt=annual_pt,
            projected_annual_take_home=annual_take_home,
            effective_tax_rate_pct=eff_rate,
            monthly_schedule=monthly_schedule,
            data_status=FinancialDataStatus.PROJECTED,
        )
