from decimal import Decimal

from app.engine.analytics.anomaly_engine import AnomalyDetectionEngine, AnomalySeverity
from app.engine.analytics.forecasting_engine import FinancialDataStatus, SalaryForecastEngine
from app.engine.analytics.simulator_service import FinancialSimulatorService


def test_salary_forecast_engine_generates_twelve_months():
    forecast = SalaryForecastEngine.generate_forecast(
        employee_id=1,
        current_monthly_gross=Decimal("100000.00"),
        annual_increment_pct=Decimal("0.10"),  # 10% raise
        increment_start_month=4,
    )

    assert forecast.data_status == FinancialDataStatus.PROJECTED
    assert len(forecast.monthly_schedule) == 12
    assert forecast.projected_annual_gross > forecast.current_annual_gross
    assert forecast.monthly_schedule[0].projected_monthly_gross == Decimal("100000.00")
    assert forecast.monthly_schedule[3].projected_monthly_gross == Decimal("110000.00")  # After month 4 increment


def test_financial_simulator_raise_and_bonus():
    # 1. Raise Simulator (+10%)
    raise_res = FinancialSimulatorService.simulate_raise(
        current_annual_gross=Decimal("1200000.00"),
        increment_pct=Decimal("0.10"),
    )
    assert raise_res.data_status == FinancialDataStatus.SIMULATED
    assert raise_res.new_annual_gross == Decimal("1320000.00")
    assert raise_res.gross_increase == Decimal("120000.00")
    assert raise_res.net_take_home_increase > 0
    assert raise_res.marginal_retention_pct > 0

    # 2. Bonus Simulator (₹1,00,000 bonus on ₹12L)
    bonus_res = FinancialSimulatorService.simulate_bonus(
        current_annual_gross=Decimal("1200000.00"),
        bonus_amount=Decimal("100000.00"),
    )
    assert bonus_res.data_status == FinancialDataStatus.SIMULATED
    assert bonus_res.new_annual_gross == Decimal("1300000.00")
    assert bonus_res.projected_additional_tax > 0
    assert bonus_res.projected_additional_take_home > 0
    assert bonus_res.projected_additional_tax + bonus_res.projected_additional_take_home == Decimal("100000.00")


def test_anomaly_detection_engine_triggers_on_significant_spike():
    # Previous: ₹60,000 -> Current: ₹90,000 (50% increase, ₹30,000 delta)
    report = AnomalyDetectionEngine.evaluate_variance(
        field_name="monthly_gross",
        previous_value=Decimal("60000.00"),
        current_value=Decimal("90000.00"),
    )

    assert report is not None
    assert report.is_anomaly is True
    assert report.severity in [AnomalySeverity.WARNING, AnomalySeverity.HIGH]
    assert "Noticeable variance" in report.explanation

    # Minor variance below threshold (₹60,000 -> ₹62,000)
    no_report = AnomalyDetectionEngine.evaluate_variance(
        field_name="monthly_gross",
        previous_value=Decimal("60000.00"),
        current_value=Decimal("62000.00"),
    )
    assert no_report is None
