import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.core.database import SessionLocal
from app.models.employee import Employee
from app.models.organization import Organization
from app.services.compensation_service import CompensationService


def test_compensation_overlap_prevention():
    """
    Verifies that CompensationService strictly blocks overlapping active date ranges for the same employee.
    """
    with SessionLocal() as db:
        # Create test tenant & employee
        org = Organization(
            legal_name="Overlap Test Org",
            display_name="Overlap Test",
            organization_code=f"OVERLAP_{uuid.uuid4().hex[:6]}",
            status="ACTIVE",
        )
        db.add(org)
        db.flush()

        emp = Employee(
            organization_id=org.id,
            employee_code=f"EMP-O-{uuid.uuid4().hex[:4]}",
            first_name="Overlap",
            last_name="Tester",
            email=f"overlap_{uuid.uuid4().hex[:6]}@test.com",
            date_of_joining=date(2025, 4, 1),
            state_id=1,
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)

        comp_service = CompensationService(db)

        # 1. Create Compensation V1 (2025-04-01 to 2025-09-30)
        v1 = comp_service.create_compensation_version(
            employee_id=emp.id,
            effective_from=date(2025, 4, 1),
            effective_to=date(2025, 9, 30),
            annual_ctc=Decimal("1200000.00"),
            monthly_gross=Decimal("100000.00"),
            components=[
                {"name": "Basic Salary", "component_type": "EARNING", "monthly_amount": Decimal("50000.00")},
                {"name": "HRA", "component_type": "EARNING", "monthly_amount": Decimal("25000.00")},
                {"name": "Special Allowance", "component_type": "EARNING", "monthly_amount": Decimal("25000.00")},
            ],
        )
        assert v1.id is not None

        # 2. Attempt to create Overlapping V2 (2025-07-01 to 2026-03-31) -> Must FAIL with ValueError
        with pytest.raises(ValueError) as exc_info:
            comp_service.create_compensation_version(
                employee_id=emp.id,
                effective_from=date(2025, 7, 1),
                effective_to=date(2026, 3, 31),
                annual_ctc=Decimal("1400000.00"),
                monthly_gross=Decimal("116666.67"),
                components=[
                    {"name": "Basic Salary", "component_type": "EARNING", "monthly_amount": Decimal("58333.33")},
                ],
            )
        assert "overlaps with an existing active compensation structure" in str(exc_info.value)

        # 3. Create Non-Overlapping V2 (2025-10-01 to 2026-03-31) -> Must SUCCEED
        v2 = comp_service.create_compensation_version(
            employee_id=emp.id,
            effective_from=date(2025, 10, 1),
            effective_to=date(2026, 3, 31),
            annual_ctc=Decimal("1400000.00"),
            monthly_gross=Decimal("116666.67"),
            components=[
                {"name": "Basic Salary", "component_type": "EARNING", "monthly_amount": Decimal("58333.33")},
                {"name": "HRA", "component_type": "EARNING", "monthly_amount": Decimal("29166.67")},
                {"name": "Special Allowance", "component_type": "EARNING", "monthly_amount": Decimal("29166.67")},
            ],
        )
        assert v2.id is not None
        assert v2.id != v1.id
