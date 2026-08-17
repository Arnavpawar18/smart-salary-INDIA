from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.compliance import TaxDeclaration, TaxDeclarationItem


class TaxDeclarationService:
    """
    Manages 6-Stage tax declarations and 3-Tier TDS computations:
    1. DRAFT -> SUBMITTED -> UNDER_REVIEW -> VERIFIED / REJECTED -> FROZEN.
    2. 3-Tier TDS:
       - Projected Annual Liability (Statutory projection)
       - Planned Monthly Withholding
       - Actual YTD Deductions
    """

    def __init__(self, db: Session):
        self.db = db

    def create_or_update_declaration(
        self,
        employee_id: int,
        organization_id: int,
        financial_year: str,
        regime: str,
        items: list[dict[str, Any]],
    ) -> TaxDeclaration:
        decl = self.db.scalar(
            select(TaxDeclaration).where(
                TaxDeclaration.employee_id == employee_id,
                TaxDeclaration.financial_year == financial_year,
                TaxDeclaration.regime == regime,
            )
        )
        if decl and decl.status == "FROZEN":
            raise ValueError(f"Tax declaration for FY {financial_year} ({regime}) is FROZEN and cannot be modified.")

        if not decl:
            decl = TaxDeclaration(
                employee_id=employee_id,
                organization_id=organization_id,
                financial_year=financial_year,
                regime=regime,
                status="DRAFT",
            )
            self.db.add(decl)
            self.db.flush()
        else:
            # Clear existing items for draft update
            for it in decl.items:
                self.db.delete(it)
            self.db.flush()

        tot_declared = Decimal("0.00")
        for it in items:
            dec_amt = Decimal(str(it.get("declared_amount", 0)))
            item = TaxDeclarationItem(
                declaration_id=decl.id,
                section_code=it["section_code"],
                category_name=it["category_name"],
                declared_amount=dec_amt,
                verified_amount=Decimal("0.00"),
                status="PENDING",
            )
            self.db.add(item)
            tot_declared += dec_amt

        decl.total_declared_deductions = tot_declared
        self.db.commit()
        self.db.refresh(decl)
        return decl

    def transition_stage(
        self,
        declaration_id: int,
        target_stage: str,
        actor_id: int | None = None,
        verified_items: list[dict[str, Any]] | None = None,
        rejection_reason: str | None = None,
    ) -> TaxDeclaration:
        """
        Executes strict 6-stage compliance transitions:
        DRAFT -> SUBMITTED -> UNDER_REVIEW -> VERIFIED / REJECTED -> FROZEN.
        """
        decl = self.db.scalar(select(TaxDeclaration).where(TaxDeclaration.id == declaration_id))
        if not decl:
            raise ValueError(f"Tax declaration {declaration_id} not found.")

        current = decl.status

        VALID_TRANSITIONS = {
            "DRAFT": ["SUBMITTED"],
            "SUBMITTED": ["UNDER_REVIEW", "DRAFT"],
            "UNDER_REVIEW": ["VERIFIED", "REJECTED"],
            "REJECTED": ["DRAFT", "SUBMITTED"],
            "VERIFIED": ["FROZEN", "UNDER_REVIEW"],
            "FROZEN": ["UNDER_REVIEW"],  # Unfreeze requires admin exception
        }

        if target_stage not in VALID_TRANSITIONS.get(current, []):
            raise ValueError(f"Invalid tax declaration stage transition from {current} to {target_stage}")

        if target_stage == "SUBMITTED":
            decl.submitted_at = datetime.now(UTC)
        elif target_stage == "VERIFIED":
            decl.verified_at = datetime.now(UTC)
            decl.verified_by = actor_id
            if verified_items:
                tot_verified = Decimal("0.00")
                for v in verified_items:
                    item_id = v["item_id"]
                    v_amt = Decimal(str(v["verified_amount"]))
                    db_item = self.db.scalar(select(TaxDeclarationItem).where(TaxDeclarationItem.id == item_id))
                    if db_item:
                        db_item.verified_amount = v_amt
                        db_item.status = "ACCEPTED"
                        tot_verified += v_amt
                decl.total_verified_deductions = tot_verified
        elif target_stage == "REJECTED":
            decl.rejection_reason = rejection_reason or "Insufficient proof"

        decl.status = target_stage
        self.db.commit()
        self.db.refresh(decl)
        return decl
