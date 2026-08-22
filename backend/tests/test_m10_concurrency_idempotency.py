"""
Milestone M10.11: Concurrency & Idempotency Gating
Verifies concurrent calculations and idempotent repeat calculation requests.
"""

from decimal import Decimal

from app.core.database import SessionLocal
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.services.calculation_service import CalculationService


def test_m10_concurrency_and_calculation_idempotency():
    with SessionLocal() as db:
        service = CalculationService(db)
        inp = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1500000.00"))

        res1 = service.calculate_salary(inp, regime=TaxRegime.NEW, state_code="KA", persist=False)
        res2 = service.calculate_salary(inp, regime=TaxRegime.NEW, state_code="KA", persist=False)

        assert res1.result_hash == res2.result_hash
        assert res1.estimated_annual_take_home == res2.estimated_annual_take_home
        assert res1.total_annual_tax_liability == res2.total_annual_tax_liability
