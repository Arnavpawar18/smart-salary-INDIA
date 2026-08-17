from decimal import Decimal

from app.core.database import SessionLocal
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.presentation.quality import CalculationQuality, QualityClassifier
from app.services.calculation_service import CalculationService
from app.services.salary_service import SalaryService
from app.services.scenario_service import ScenarioService


def test_quality_classifier_states():
    # 1. Quick mode with standard assumptions -> ESTIMATE
    q1 = QualityClassifier.classify(is_quick_mode=True, has_custom_components=False, is_supported=True)
    assert q1["status"] == CalculationQuality.ESTIMATE.value
    assert "Quick Estimate" in q1["badge_label"]

    # 2. Detailed mode with custom components -> DETAILED
    q2 = QualityClassifier.classify(is_quick_mode=False, has_custom_components=True, is_supported=True)
    assert q2["status"] == CalculationQuality.DETAILED.value
    assert "Detailed Calculation" in q2["badge_label"]

    # 3. Unsupported state or FY -> UNSUPPORTED
    q3 = QualityClassifier.classify(is_quick_mode=False, has_custom_components=False, is_supported=False)
    assert q3["status"] == CalculationQuality.UNSUPPORTED.value


def test_salary_service_monthly_projection_and_mh_february():
    with SessionLocal() as db:
        calc_svc = CalculationService(db)
        inp = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1200000.00"))
        res = calc_svc.calculate_salary(inp, regime=TaxRegime.NEW, state_code="MH", persist=False)

        schedule = SalaryService.generate_monthly_schedule(res)
        assert len(schedule) == 12

        # Verify MH February PT is ₹300, others ₹200
        feb_row = [r for r in schedule if r.month_name == "Feb"][0]
        jan_row = [r for r in schedule if r.month_name == "Jan"][0]
        assert feb_row.professional_tax == Decimal("300.00")
        assert jan_row.professional_tax == Decimal("200.00")

        # Verify employer contributions are isolated and positive
        assert feb_row.employer_eps > Decimal("0.00")
        assert feb_row.total_employer_contribution > Decimal("0.00")


def test_scenario_service_what_if_and_marginal_retention():
    with SessionLocal() as db:
        scenario_svc = ScenarioService(db)
        sim = scenario_svc.calculate_what_if_raises(
            base_salary=Decimal("1200000.00"),
            financial_year="2025-26",
            state_code="KA",
            regime=TaxRegime.NEW,
            raise_percentages=[Decimal("5"), Decimal("10"), Decimal("20")],
        )

        assert sim["base_gross"] == Decimal("1200000.00")
        assert len(sim["simulations"]) == 3

        sim10 = sim["simulations"][1]  # 10% raise
        assert sim10["simulated_gross"] == Decimal("1320000.00")
        assert sim10["gross_delta"] == Decimal("1200000.00") * Decimal("0.10")
        assert sim10["take_home_delta"] > Decimal("0.00")
        assert sim10["marginal_retention_rate"] > Decimal("0.00")


def test_what_changed_delta_explanation():
    with SessionLocal() as db:
        calc_svc = CalculationService(db)
        scenario_svc = ScenarioService(db)

        inp_before = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1000000.00"))
        inp_after = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1200000.00"))

        res_before = calc_svc.calculate_salary(inp_before, regime=TaxRegime.NEW, state_code="KA", persist=False)
        res_after = calc_svc.calculate_salary(inp_after, regime=TaxRegime.NEW, state_code="KA", persist=False)

        delta = scenario_svc.compute_what_changed_delta(res_before, res_after)
        assert delta["gross_delta"] == Decimal("200000.00")
        assert delta["take_home_delta"] > Decimal("0.00")
        assert len(delta["narrative"]) >= 3
