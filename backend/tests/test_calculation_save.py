import uuid
from datetime import date
from decimal import Decimal

from app.core.database import SessionLocal
from app.core.security import PasswordHasher
from app.models.auth import User
from app.models.employee import Employee
from app.services.calculation_save_service import CalculationSaveService


def test_calculation_save_and_supersede_lifecycle():
    with SessionLocal() as db:
        # Create Employee
        email = f"calc_test_{uuid.uuid4().hex[:8]}@smartsalary.in"
        user = User(email=email, hashed_password=PasswordHasher.hash_password("Pass123!"), full_name="Calc User")
        db.add(user)
        db.flush()

        emp = Employee(
            user_id=user.id,
            employee_code=f"EMP-{user.id:04d}",
            first_name="Calc",
            last_name="User",
            email=email,
            date_of_joining=date.today(),
            state_id=1,
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)

        service = CalculationSaveService(db)

        # 1. Save first calculation for FY 2025-26 -> Status CURRENT
        calc1 = service.save_calculation_for_employee(
            employee_id=emp.id,
            financial_year="2025-26",
            regime="NEW",
            annual_gross=Decimal("1200000.00"),
            taxable_income=Decimal("1125000.00"),
            total_tax=Decimal("97500.00"),
            take_home=Decimal("1102500.00"),
            result_snapshot={"annual_gross": "1200000.00"},
            trace_events=[],
        )
        assert calc1.status == "CURRENT"

        # 2. Save second calculation for FY 2025-26 -> First should be SUPERSEDED, second CURRENT
        calc2 = service.save_calculation_for_employee(
            employee_id=emp.id,
            financial_year="2025-26",
            regime="NEW",
            annual_gross=Decimal("1500000.00"),
            taxable_income=Decimal("1425000.00"),
            total_tax=Decimal("150000.00"),
            take_home=Decimal("1350000.00"),
            result_snapshot={"annual_gross": "1500000.00"},
            trace_events=[],
        )
        assert calc2.status == "CURRENT"

        # Verify calc1 is now SUPERSEDED
        db.refresh(calc1)
        assert calc1.status == "SUPERSEDED"

        # 3. Object-level IDOR Defense Test
        # Employee 9999 must NOT be able to access calc2
        assert service.get_employee_calculation_by_id(employee_id=9999, calculation_id=calc2.id) is None
        # True owner CAN access calc2
        assert service.get_employee_calculation_by_id(employee_id=emp.id, calculation_id=calc2.id) is not None
