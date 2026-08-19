from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payslip import PayslipDocument, PayslipExtraction, PayslipValidation


class PayslipRepository:
    """
    Database repository for Payslip documents, extractions, validations, and corrections.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_document(
        self,
        employee_id: int,
        file_name: str,
        file_path: str,
        file_size_bytes: int,
        file_hash: str,
        mime_type: str = "application/pdf",
        status: str = "UPLOADED",
    ) -> PayslipDocument:
        doc = PayslipDocument(
            employee_id=employee_id,
            file_name=file_name,
            file_path=file_path,
            file_size_bytes=file_size_bytes,
            file_hash=file_hash,
            mime_type=mime_type,
            status=status,
        )
        self.db.add(doc)
        self.db.flush()
        return doc

    def find_by_hash(self, employee_id: int, file_hash: str) -> PayslipDocument | None:
        """Deduplication lookup by SHA-256 hash."""
        return self.db.scalar(
            select(PayslipDocument).where(
                PayslipDocument.employee_id == employee_id,
                PayslipDocument.file_hash == file_hash,
            )
        )

    def get_document_by_id(self, document_id: int) -> PayslipDocument | None:
        return self.db.scalar(select(PayslipDocument).where(PayslipDocument.id == document_id))

    def list_employee_documents(self, employee_id: int) -> list[PayslipDocument]:
        return list(
            self.db.scalars(
                select(PayslipDocument)
                .where(PayslipDocument.employee_id == employee_id)
                .order_by(PayslipDocument.created_at.desc())
            ).all()
        )

    def save_extraction(
        self,
        document_id: int,
        extracted_data: dict[str, Any],
        confidence_score: Decimal,
        ocr_engine_used: str | None = None,
        raw_text: str | None = None,
    ) -> PayslipExtraction:
        extraction = PayslipExtraction(
            document_id=document_id,
            extracted_data=extracted_data,
            confidence_score=confidence_score,
            ocr_engine_used=ocr_engine_used,
            raw_text=raw_text,
        )
        self.db.add(extraction)
        self.db.flush()
        return extraction

    def save_validation(
        self,
        document_id: int,
        validation_status: str,
        discrepancy_flags: dict[str, Any],
        reconciliation_notes: str | None = None,
    ) -> PayslipValidation:
        # Check if validation record exists, update or create
        val = self.db.scalar(select(PayslipValidation).where(PayslipValidation.document_id == document_id))
        if val:
            val.validation_status = validation_status
            val.discrepancy_flags = discrepancy_flags
            val.reconciliation_notes = reconciliation_notes
        else:
            val = PayslipValidation(
                document_id=document_id,
                validation_status=validation_status,
                discrepancy_flags=discrepancy_flags,
                reconciliation_notes=reconciliation_notes,
            )
            self.db.add(val)
        self.db.flush()
        return val

    def record_correction_event(
        self,
        document_id: int,
        correction_payload: dict[str, Any],
    ) -> PayslipValidation:
        """
        Appends an immutable correction event to discrepancy_flags['corrections_history']
        without overwriting the original PayslipExtraction record.
        """
        val = self.db.scalar(select(PayslipValidation).where(PayslipValidation.document_id == document_id))
        if not val:
            val = PayslipValidation(
                document_id=document_id,
                validation_status="CORRECTED",
                discrepancy_flags={"corrections_history": [correction_payload]},
            )
            self.db.add(val)
        else:
            flags = dict(val.discrepancy_flags)
            history = list(flags.get("corrections_history", []))
            history.append(correction_payload)
            flags["corrections_history"] = history
            val.discrepancy_flags = flags
            val.validation_status = "CORRECTED"
        self.db.flush()
        return val
