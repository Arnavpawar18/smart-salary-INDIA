from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.models.auth import User
from app.models.employee import Employee
from app.services.calculation_context_service import CalculationContext, resolve_owned_calculation
from app.services.calculation_service import CalculationService


def test_calculation_context_resolver_single_source_of_truth(db_session: Session):
    # 1. Create User A and Employee A
    user_a = User(
        email="usera_context@example.com",
        hashed_password="hashed_password_123",
        full_name="User Alpha",
        is_active=True,
    )
    db_session.add(user_a)
    db_session.flush()

    emp_a = Employee(
        user_id=user_a.id,
        employee_code="EMP-CTX-01",
        first_name="User",
        last_name="Alpha",
        email=user_a.email,
        date_of_joining=date.today(),
        employment_type="FULL_TIME",
    )
    db_session.add(emp_a)
    db_session.flush()

    # 2. Run Calculation A (Salary: ₹12,00,000)
    service = CalculationService(db_session)
    calc_inp_a = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1200000.00"))
    service.calculate_salary(
        salary_input=calc_inp_a,
        regime=TaxRegime.NEW,
        state_code="KA",
        employee_id=emp_a.id,
        persist=True,
    )

    # Fetch calculation run ID
    calc_id_a = emp_a.calculation_runs[0].id

    # 3. Resolve context for User A
    ctx_a = resolve_owned_calculation(db=db_session, calculation_id=calc_id_a, user=user_a)
    assert isinstance(ctx_a, CalculationContext)
    assert ctx_a.calculation_id == calc_id_a
    assert ctx_a.user_id == user_a.id
    assert ctx_a.employee_id == emp_a.id
    assert ctx_a.financial_year == "2025-26"
    assert ctx_a.regime == "NEW"
    assert ctx_a.state == "KA"
    assert "estimated_annual_take_home" in ctx_a.output_snapshot
    assert len(ctx_a.calculation_trace) > 0


def test_calculation_ab_isolation_and_cross_user_denial(db_session: Session):
    # Setup User A
    user_a = User(email="usera_ab@example.com", hashed_password="pwd", full_name="User A", is_active=True)
    db_session.add(user_a)
    db_session.flush()
    emp_a = Employee(
        user_id=user_a.id,
        employee_code="EMP-A",
        first_name="A",
        last_name="User",
        email=user_a.email,
        date_of_joining=date.today(),
    )
    db_session.add(emp_a)

    # Setup User B
    user_b = User(email="userb_ab@example.com", hashed_password="pwd", full_name="User B", is_active=True)
    db_session.add(user_b)
    db_session.flush()
    emp_b = Employee(
        user_id=user_b.id,
        employee_code="EMP-B",
        first_name="B",
        last_name="User",
        email=user_b.email,
        date_of_joining=date.today(),
    )
    db_session.add(emp_b)
    db_session.flush()

    service = CalculationService(db_session)

    # Calculation A: ₹10,00,000 in KA
    calc_inp_a = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1000000.00"))
    service.calculate_salary(calc_inp_a, regime=TaxRegime.NEW, state_code="KA", employee_id=emp_a.id, persist=True)

    # Calculation B: ₹25,00,000 in MH
    calc_inp_b = SalaryInput(financial_year="2025-26", annual_gross=Decimal("2500000.00"))
    service.calculate_salary(calc_inp_b, regime=TaxRegime.NEW, state_code="MH", employee_id=emp_a.id, persist=True)

    calc_runs = emp_a.calculation_runs
    calc_id_a = calc_runs[0].id
    calc_id_b = calc_runs[1].id

    # Resolve Context A & Context B
    ctx_a = resolve_owned_calculation(db=db_session, calculation_id=calc_id_a, user=user_a)
    ctx_b = resolve_owned_calculation(db=db_session, calculation_id=calc_id_b, user=user_a)

    # Verify A != B isolation invariants
    assert ctx_a.calculation_id != ctx_b.calculation_id
    assert ctx_a.state == "KA"
    assert ctx_b.state == "MH"
    assert Decimal(str(ctx_a.output_snapshot["annual_gross_salary"])) == Decimal("1000000.00")
    assert Decimal(str(ctx_b.output_snapshot["annual_gross_salary"])) == Decimal("2500000.00")
    assert ctx_a.output_snapshot["total_annual_tax_liability"] != ctx_b.output_snapshot["total_annual_tax_liability"]

    # Test Cross-User IDOR Access Denial: User B trying to resolve User A's calculation
    with pytest.raises(HTTPException) as exc_info:
        resolve_owned_calculation(db=db_session, calculation_id=calc_id_a, user=user_b)
    assert exc_info.value.status_code == 403
