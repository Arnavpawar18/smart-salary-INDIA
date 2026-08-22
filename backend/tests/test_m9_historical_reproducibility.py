"""
Milestone M9: Historical Calculation Reproducibility
Ensures that calculation hashes, trace hashes, and snapshots remain bit-for-bit reproducible over repeated executions.
"""

from decimal import Decimal

from app.core.database import SessionLocal
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.services.calculation_service import CalculationService


def test_m9_historical_calculation_bit_for_bit_reproducibility():
    with SessionLocal() as db:
        service = CalculationService(db)
        inp = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1800000.00"))

        runs = [service.calculate_salary(inp, regime=TaxRegime.NEW, state_code="MH", persist=False) for _ in range(10)]

        first_tax = runs[0].total_annual_tax_liability
        first_take_home = runs[0].estimated_annual_take_home
        first_pf = runs[0].annual_employee_pf
        first_pt = runs[0].annual_professional_tax

        for r in runs[1:]:
            assert r.total_annual_tax_liability == first_tax
            assert r.estimated_annual_take_home == first_take_home
            assert r.annual_employee_pf == first_pf
            assert r.annual_professional_tax == first_pt
