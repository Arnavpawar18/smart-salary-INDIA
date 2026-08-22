"""
Milestone M9.6: Independent Regulatory Oracle Layer Tests
Validates production engine calculation against independent statutory oracle with clean-room formulas.
"""

from decimal import Decimal

import pytest

from app.core.database import SessionLocal
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.engine.oracle.independent_oracle import IndependentRegulatoryOracle
from app.services.calculation_service import CalculationService


@pytest.mark.parametrize(
    "gross_salary,state",
    [
        (Decimal("600000.00"), "KA"),
        (Decimal("1200000.00"), "KA"),
        (Decimal("1275000.00"), "MH"),
        (Decimal("1575000.00"), "MH"),
        (Decimal("2500000.00"), "TS"),
        (Decimal("5000000.00"), "WB"),
    ],
)
def test_m9_oracle_parity_across_salary_spectrum(gross_salary, state):
    oracle_res = IndependentRegulatoryOracle.calculate_fy2025_26_new(gross_salary, state)

    with SessionLocal() as db:
        service = CalculationService(db)
        inp = SalaryInput(financial_year="2025-26", annual_gross=gross_salary)
        engine_res = service.calculate_salary(inp, regime=TaxRegime.NEW, state_code=state, persist=False)

        assert engine_res.annual_gross_salary == oracle_res.annual_gross
        assert engine_res.taxable_income == oracle_res.taxable_income
        assert engine_res.standard_deduction == oracle_res.standard_deduction
        assert engine_res.slab_tax == oracle_res.slab_tax
        assert engine_res.section_87a_rebate == oracle_res.section_87a_rebate
        assert engine_res.total_annual_tax_liability == oracle_res.total_tax
        assert engine_res.annual_employee_pf == oracle_res.annual_employee_pf
        assert engine_res.annual_professional_tax == oracle_res.annual_professional_tax
        assert engine_res.estimated_annual_take_home == oracle_res.annual_take_home
        assert engine_res.estimated_monthly_take_home == oracle_res.monthly_take_home
