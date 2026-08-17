from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.salary import SalaryComponent, SalaryRecord


class CompensationService:
    """
    Manages versioned, effective-dated employee compensation structures.
    CRITICAL INVARIANT: Active compensation date ranges for the same employee MUST NOT overlap.
    """

    def __init__(self, db: Session):
        self.db = db

    def check_date_overlap(
        self,
        employee_id: int,
        effective_from: date,
        effective_to: date | None = None,
        exclude_record_id: int | None = None,
    ) -> bool:
        """
        Returns True if the proposed [effective_from, effective_to] range overlaps
        with any existing ACTIVE/APPROVED compensation record for this employee.
        """
        # Fetch existing active records for employee
        stmt = select(SalaryRecord).where(
            SalaryRecord.employee_id == employee_id,
        )
        if exclude_record_id:
            stmt = stmt.where(SalaryRecord.id != exclude_record_id)

        existing_records = list(self.db.scalars(stmt).all())

        eff_to = effective_to or date(9999, 12, 31)

        for rec in existing_records:
            rec_from = rec.effective_from
            rec_to = rec.effective_to or date(9999, 12, 31)

            # Overlap condition: max(start1, start2) <= min(end1, end2)
            overlap_start = max(effective_from, rec_from)
            overlap_end = min(eff_to, rec_to)

            if overlap_start <= overlap_end:
                return True

        return False

    def create_compensation_version(
        self,
        employee_id: int,
        effective_from: date,
        annual_ctc: Decimal,
        monthly_gross: Decimal,
        components: list[dict[str, Any]],
        effective_to: date | None = None,
        reason: str = "Annual Revision",
        created_by: int | None = None,
    ) -> SalaryRecord:
        """
        Creates a new versioned compensation structure with strict overlap validation.
        """
        if self.check_date_overlap(employee_id, effective_from, effective_to):
            raise ValueError(
                f"Compensation date range {effective_from} to {effective_to or 'Indefinite'} "
                f"overlaps with an existing active compensation structure for employee {employee_id}."
            )

        # 1. Create SalaryRecord
        salary_rec = SalaryRecord(
            employee_id=employee_id,
            effective_from=effective_from,
            effective_to=effective_to,
            annual_ctc=annual_ctc,
            monthly_gross=monthly_gross,
        )
        self.db.add(salary_rec)
        self.db.flush()

        # 2. Create granular components
        for comp in components:
            sc = SalaryComponent(
                salary_record_id=salary_rec.id,
                name=comp["name"],
                component_type=comp["component_type"],  # EARNING, DEDUCTION, STATUTORY, EMPLOYER_CONTRIBUTION
                monthly_amount=Decimal(str(comp["monthly_amount"])),
                annual_amount=Decimal(str(comp.get("annual_amount", comp["monthly_amount"] * 12))),
                is_taxable=comp.get("is_taxable", True),
            )
            self.db.add(sc)

        self.db.commit()
        self.db.refresh(salary_rec)
        return salary_rec
