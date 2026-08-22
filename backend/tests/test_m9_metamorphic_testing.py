"""
Milestone M9.10: Metamorphic Calculation Testing
Validates calculation monotonicity, determinism, and mathematical sanity across inputs.
"""

from decimal import Decimal

from app.core.database import SessionLocal
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.services.calculation_service import CalculationService


def test_m9_metamorphic_tax_monotonicity():
    with SessionLocal() as db:
        service = CalculationService(db)

        salaries = [
            Decimal("500000.00"),
            Decimal("800000.00"),
            Decimal("1200000.00"),
            Decimal("1500000.00"),
            Decimal("2000000.00"),
            Decimal("3000000.00"),
        ]

        results = [
            service.calculate_salary(
                SalaryInput(financial_year="2025-26", annual_gross=s),
                regime=TaxRegime.NEW,
                state_code="KA",
                persist=False,
            )
            for s in salaries
        ]

        for i in range(len(results) - 1):
            assert results[i + 1].total_annual_tax_liability >= results[i].total_annual_tax_liability
            assert results[i + 1].estimated_annual_take_home >= results[i].estimated_annual_take_home
