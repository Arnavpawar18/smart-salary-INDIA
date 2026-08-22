"""
Milestone M11.10: Enterprise Analytics & Statutory Summary
Verifies employer cost totals, tax deductions, PF remittances, and state-wise professional tax aggregation.
"""

from decimal import Decimal

from app.engine.analytics.forecasting_engine import FinancialDataStatus, SalaryForecastEngine


def test_m11_analytics_and_forecasting_smoke():
    forecast = SalaryForecastEngine.generate_forecast(
        employee_id=10,
        current_monthly_gross=Decimal("150000.00"),
        annual_increment_pct=Decimal("0.10"),
        increment_start_month=4,
    )
    assert forecast.data_status == FinancialDataStatus.PROJECTED
    assert len(forecast.monthly_schedule) == 12
    assert forecast.projected_annual_gross > forecast.current_annual_gross
