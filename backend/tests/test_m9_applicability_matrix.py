"""
Milestone M9.3: Statutory Applicability Matrix
Verifies applicability of PF, PT, Gratuity, and Income Tax deductions across wage thresholds and components.
"""

from decimal import Decimal

from app.core.database import SessionLocal
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.services.calculation_service import CalculationService


def test_m9_pf_statutory_ceiling_and_uncapped_options():
    with SessionLocal() as db:
        service = CalculationService(db)

        # High gross salary (15 LPA -> Basic 7.5LPA = 62.5k/mo)
        # Default capped PF: 12% of 15,000 = 1,800/mo = 21,600/yr
        inp_capped = SalaryInput(
            financial_year="2025-26", annual_gross=Decimal("1500000.00"), pf_opt_in_higher_wage=False
        )
        res_capped = service.calculate_salary(inp_capped, regime=TaxRegime.NEW, state_code="KA", persist=False)
        assert res_capped.annual_employee_pf == Decimal("21600.00")
        assert res_capped.monthly_employee_pf == Decimal("1800.00")

        # Uncapped PF: 12% of 62,500 = 7,500/mo = 90,000/yr
        inp_uncapped = SalaryInput(
            financial_year="2025-26", annual_gross=Decimal("1500000.00"), pf_opt_in_higher_wage=True
        )
        res_uncapped = service.calculate_salary(inp_uncapped, regime=TaxRegime.NEW, state_code="KA", persist=False)
        assert res_uncapped.annual_employee_pf == Decimal("90000.00")
        assert res_uncapped.monthly_employee_pf == Decimal("7500.00")
