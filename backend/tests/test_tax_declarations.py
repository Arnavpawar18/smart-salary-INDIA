import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.core.database import SessionLocal
from app.models.employee import Employee
from app.models.organization import Organization
from app.services.tax_declaration_service import TaxDeclarationService


def test_tax_declaration_six_stage_lifecycle_and_transition_invariants():
    """
    Verifies that TaxDeclarationService enforces:
    1. 6-stage compliance workflow: DRAFT -> SUBMITTED -> UNDER_REVIEW -> VERIFIED -> FROZEN
    2. Invalid stage transitions are blocked fail-closed with ValueError
    3. Item verification amounts roll up into total_verified_deductions
    """
    with SessionLocal() as db:
        # Create Org & Employee
        org = Organization(
            legal_name="Compliance Test Org",
            display_name="Compliance Org",
            organization_code=f"COMP_{uuid.uuid4().hex[:6]}",
            status="ACTIVE",
        )
        db.add(org)
        db.flush()

        emp = Employee(
            organization_id=org.id,
            employee_code=f"EMP-C-{uuid.uuid4().hex[:4]}",
            first_name="Compliance",
            last_name="Officer",
            email=f"compliance_{uuid.uuid4().hex[:6]}@org.com",
            date_of_joining=date(2025, 4, 1),
            state_id=1,
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)

        decl_svc = TaxDeclarationService(db)

        # 1. Create DRAFT declaration
        decl = decl_svc.create_or_update_declaration(
            employee_id=emp.id,
            organization_id=org.id,
            financial_year="2026-27",
            regime="OLD",
            items=[
                {"section_code": "80C", "category_name": "Public Provident Fund", "declared_amount": Decimal("150000.00")},
                {"section_code": "80D", "category_name": "Health Insurance", "declared_amount": Decimal("25000.00")},
            ],
        )
        assert decl.status == "DRAFT"
        assert decl.total_declared_deductions == Decimal("175000.00")
        assert len(decl.items) == 2

        # 2. Stage: DRAFT -> SUBMITTED
        decl = decl_svc.transition_stage(decl.id, "SUBMITTED")
        assert decl.status == "SUBMITTED"
        assert decl.submitted_at is not None

        # 3. Invalid jump: SUBMITTED -> FROZEN (Must Fail)
        with pytest.raises(ValueError) as exc_info:
            decl_svc.transition_stage(decl.id, "FROZEN")
        assert "Invalid tax declaration stage transition" in str(exc_info.value)

        # 4. Stage: SUBMITTED -> UNDER_REVIEW
        decl = decl_svc.transition_stage(decl.id, "UNDER_REVIEW")
        assert decl.status == "UNDER_REVIEW"

        # 5. Stage: UNDER_REVIEW -> VERIFIED (with verified items)
        item_80c = decl.items[0]
        item_80d = decl.items[1]
        decl = decl_svc.transition_stage(
            decl.id,
            "VERIFIED",
            actor_id=1,
            verified_items=[
                {"item_id": item_80c.id, "verified_amount": Decimal("150000.00")},
                {"item_id": item_80d.id, "verified_amount": Decimal("20000.00")},  # partially verified
            ],
        )
        assert decl.status == "VERIFIED"
        assert decl.total_verified_deductions == Decimal("170000.00")

        # 6. Stage: VERIFIED -> FROZEN
        decl = decl_svc.transition_stage(decl.id, "FROZEN")
        assert decl.status == "FROZEN"

        # 7. Attempt update on FROZEN declaration must fail
        with pytest.raises(ValueError) as exc_info:
            decl_svc.create_or_update_declaration(
                employee_id=emp.id,
                organization_id=org.id,
                financial_year="2026-27",
                regime="OLD",
                items=[{"section_code": "80C", "category_name": "PPF", "declared_amount": Decimal("100000.00")}],
            )
        assert "FROZEN" in str(exc_info.value)
