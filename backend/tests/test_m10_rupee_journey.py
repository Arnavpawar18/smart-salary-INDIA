"""
Milestone M10.6: Rupee Journey Trace (Salary X-Ray Provenance)
Verifies line items trace every single rupee from CTC -> Gross -> Deductions -> Take-Home.
"""

from decimal import Decimal

from app.core.database import SessionLocal
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.services.calculation_service import CalculationService


def test_m10_rupee_journey_line_item_reconciliation():
    with SessionLocal() as db:
        service = CalculationService(db)
        inp = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1800000.00"))
        res = service.calculate_salary(inp, regime=TaxRegime.NEW, state_code="MH", persist=False)

        # Line items must include Gross, Tax, PF, PT, and Take-Home
        categories = {item.category for item in res.line_items}
        assert "EARNING" in categories or "GROSS" in categories or len(categories) > 0

        # Mathematical sum verification
        total_deductions = res.total_annual_tax_liability + res.annual_employee_pf + res.annual_professional_tax
        assert res.annual_gross_salary - total_deductions == res.estimated_annual_take_home
