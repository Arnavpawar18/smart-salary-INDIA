from decimal import Decimal
import pytest
from app.engine.common.errors import InvalidSalaryInputError
from app.engine.dto.salary_dto import SalaryInput
from app.engine.normalizer.salary_normalizer import SalaryNormalizer


def test_normalize_annual_gross_default_breakdown():
    inp = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1200000.00"))
    norm = SalaryNormalizer.normalize(inp)

    assert norm.annual_gross == Decimal("1200000.00")
    assert norm.monthly_gross == Decimal("100000.00")
    assert norm.basic_salary == Decimal("600000.00")  # 50%
    assert norm.hra == Decimal("240000.00")           # 20%
    assert norm.special_allowance == Decimal("360000.00")  # 30%
    assert norm.pf_wage_base_monthly == Decimal("50000.00")


def test_normalize_monthly_gross_annualization():
    inp = SalaryInput(financial_year="2025-26", monthly_gross=Decimal("50000.00"))
    norm = SalaryNormalizer.normalize(inp)

    assert norm.annual_gross == Decimal("600000.00")
    assert norm.monthly_gross == Decimal("50000.00")


def test_normalize_custom_components():
    inp = SalaryInput(
        financial_year="2025-26",
        basic_salary=Decimal("500000.00"),
        hra=Decimal("200000.00"),
        special_allowance=Decimal("300000.00"),
        other_employee_deductions=Decimal("15000.00"),
    )
    norm = SalaryNormalizer.normalize(inp)

    assert norm.annual_gross == Decimal("1000000.00")
    assert norm.basic_salary == Decimal("500000.00")
    assert norm.other_employee_deductions == Decimal("15000.00")


def test_normalize_negative_salary_raises_error():
    with pytest.raises(InvalidSalaryInputError):
        SalaryNormalizer.normalize(SalaryInput(financial_year="2025-26", annual_gross=Decimal("-50000.00")))
