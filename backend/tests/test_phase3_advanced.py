from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.engine.common.enums import CalculationStatus, TaxRegime
from app.engine.dto.result_dto import CalculationAssumptions, VerifiedCalculationResult
from app.schemas.salary_input import ComprehensiveSalaryInputSchema
from app.services.history_service import HistoryService
from app.services.insight_service import InsightService


def test_salary_input_schema_conflict_detection():
    # Valid: only monthly supplied
    s1 = ComprehensiveSalaryInputSchema(monthly_gross_salary=Decimal("100000.00"))
    assert s1.monthly_gross_salary == Decimal("100000.00")

    # Valid: both supplied and consistent (100k/mo == 1.2M/yr)
    s2 = ComprehensiveSalaryInputSchema(
        monthly_gross_salary=Decimal("100000.00"),
        annual_gross_salary=Decimal("1200000.00"),
    )
    assert s2.annual_gross_salary == Decimal("1200000.00")

    # Invalid: conflicting monthly and annual gross
    with pytest.raises(ValidationError):
        ComprehensiveSalaryInputSchema(
            monthly_gross_salary=Decimal("100000.00"),
            annual_gross_salary=Decimal("1500000.00"),  # Conflict!
        )

    # Invalid: non-positive or negative salary
    with pytest.raises(ValidationError):
        ComprehensiveSalaryInputSchema(monthly_gross_salary=Decimal("-5000.00"))

    # Invalid: age boundary
    with pytest.raises(ValidationError):
        ComprehensiveSalaryInputSchema(annual_gross_salary=Decimal("1200000.00"), age=15)


def test_insight_service_disclaimer_and_generation():
    assumptions = CalculationAssumptions(
        salary_income_only=True,
        residential_status="RESIDENT",
        age=25,
        state="KA",
        pf_applicable=True,
        pf_opt_in_higher_wage=False,
        tds_provided=False,
        other_income_provided=False,
        notes=[],
    )
    mock_res = VerifiedCalculationResult(
        engine_version="CALC-1.0.0",
        rounding_policy_version="ROUND-1.0.0",
        status=CalculationStatus.VERIFIED,
        financial_year="2025-26",
        regime=TaxRegime.NEW,
        state_code="KA",
        annual_gross_salary=Decimal("1200000.00"),
        standard_deduction=Decimal("75000.00"),
        taxable_income=Decimal("1125000.00"),
        slab_tax=Decimal("62500.00"),
        section_87a_rebate=Decimal("62500.00"),
        rebate_marginal_relief=Decimal("0.00"),
        tax_after_rebate=Decimal("0.00"),
        surcharge=Decimal("0.00"),
        surcharge_marginal_relief=Decimal("0.00"),
        health_education_cess=Decimal("0.00"),
        total_annual_tax_liability=Decimal("0.00"),
        estimated_monthly_tax=Decimal("0.00"),
        annual_employee_pf=Decimal("21600.00"),
        monthly_employee_pf=Decimal("1800.00"),
        annual_employer_contribution=Decimal("21600.00"),
        monthly_employer_contribution=Decimal("1800.00"),
        annual_professional_tax=Decimal("2400.00"),
        monthly_professional_tax=Decimal("200.00"),
        other_employee_deductions=Decimal("0.00"),
        estimated_annual_take_home=Decimal("1176000.00"),
        estimated_monthly_take_home=Decimal("98000.00"),
        assumptions=assumptions,
        line_items=[],
        trace_steps=[],
        tax_rule_version_code="TRV-2025-26-NEW-v1",
        pf_rule_version_code="PFRV-2025-26-v1",
        pt_rule_version_code="KA-PT-2025-26-v1",
        input_hash="a" * 64,
        result_hash="b" * 64,
        rule_set_hash="c" * 64,
    )

    insights = InsightService.generate_insights(mock_res)
    assert len(insights) >= 2
    assert "Standard Deduction" in insights[0]["title"]
    assert "Educational Notice" in InsightService.DISCLAIMER


def test_history_service_guest_session_token():
    token1 = HistoryService.generate_guest_session_token()
    token2 = HistoryService.generate_guest_session_token()
    assert len(token1) >= 24
    assert token1 != token2

    history = HistoryService.append_calculation_to_guest_history(
        session_history=[],
        calculation_summary={"id": 1, "take_home": "11,76,000"},
        max_items=3,
    )
    assert len(history) == 1
    assert history[0]["id"] == 1
