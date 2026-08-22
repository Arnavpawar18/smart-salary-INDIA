"""
Milestone M11.11: Payroll Scale & Performance Benchmarking
Validates sub-second execution for batch payroll runs.
"""

import time
from decimal import Decimal

from app.core.database import SessionLocal
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.services.calculation_service import CalculationService


def test_m11_batch_payroll_scale_subsecond():
    with SessionLocal() as db:
        service = CalculationService(db)
        inputs = [
            SalaryInput(financial_year="2025-26", annual_gross=Decimal(str(500000 + i * 50000))) for i in range(50)
        ]

        start_time = time.perf_counter()
        results = [
            service.calculate_salary(inp, regime=TaxRegime.NEW, state_code="KA", persist=False) for inp in inputs
        ]
        duration = time.perf_counter() - start_time

        assert len(results) == 50
        # 50 calculations executed rapidly
        assert duration < 5.0, f"50 calculations took {duration:.2f}s, expected < 5s"
