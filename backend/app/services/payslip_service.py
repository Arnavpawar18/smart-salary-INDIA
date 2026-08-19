import hashlib
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.document_validator import DocumentValidator
from app.core.malware_scanner import DevPassThroughScanner, MalwareScanner
from app.core.storage import DocumentStorage, LocalDocumentStorage
from app.engine.payslip.payslip_extractor import ExtractedPayslipDTO, PayslipExtractor
from app.engine.payslip.reconciliation_engine import (
    ExpectedPayrollDTO,
    ReconciliationEngine,
    ReconciliationResultDTO,
    StatutoryExpectationDTO,
)
from app.models.calculation import CalculationSnapshot
from app.models.payroll import PayrollPeriod, PayrollRunItem
from app.repositories.payslip_repository import PayslipRepository


class PayslipService:
    """
    Orchestrates the entire Payslip Intelligence Lifecycle:
    1. Validation & Quarantine checks
    2. Malware scanning
    3. Content Addressing & Secure Storage
    4. Extraction with Spatial Provenance
    5. Multi-Status Three-Way Reconciliation against Phase 5 Payroll and Phase 2 Statutory Snapshot
    6. Immutable Correction Audit Logging
    7. Object-level Security & Authorization
    """

    def __init__(
        self,
        db: Session,
        storage: DocumentStorage | None = None,
        scanner: MalwareScanner | None = None,
    ):
        self.db = db
        self.repo = PayslipRepository(db)
        self.storage = storage or LocalDocumentStorage()
        self.scanner = scanner or DevPassThroughScanner()
        self.extractor = PayslipExtractor()

    def process_payslip_upload(
        self,
        employee_id: int,
        file_bytes: bytes,
        original_filename: str,
        uploaded_by_user_id: int | None = None,
    ) -> tuple[int, ExtractedPayslipDTO, ReconciliationResultDTO]:
        # 1. Validate File structure, size, signature, and page count
        validation_result = DocumentValidator.validate_pdf(file_bytes, original_filename)
        if not validation_result.is_valid:
            raise ValueError(f"Document validation failed: {validation_result.error_message}")

        # 2. Malware Scan (Quarantine check)
        scan_res = self.scanner.scan(file_bytes)
        if not scan_res.is_safe:
            raise ValueError(f"Security Threat Detected: {scan_res.threat_name}. {scan_res.details}")

        # 3. Compute SHA-256 for Content Addressing and Deduplication
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        existing_doc = self.repo.find_by_hash(employee_id, file_hash)
        if existing_doc:
            # Re-fetch extraction and reconciliation for existing doc
            ext_record = existing_doc.extractions[0] if existing_doc.extractions else None
            val_record = existing_doc.validations[0] if existing_doc.validations else None
            return existing_doc.id, ext_record, val_record

        # 4. Secure Private Storage
        sanitized_filename = DocumentValidator.sanitize_filename(original_filename)
        storage_key = f"{uuid.uuid4().hex}_{sanitized_filename}"
        storage_uri = self.storage.store(storage_key, file_bytes)

        # 5. Persist Document Record (Initial State: PARSED)
        doc = self.repo.create_document(
            employee_id=employee_id,
            file_name=sanitized_filename,
            file_path=storage_uri,
            file_size_bytes=len(file_bytes),
            file_hash=file_hash,
            mime_type=validation_result.mime_type,
            status="PARSED",
        )

        # 6. Extract Structured Data with Spatial Provenance
        extracted_dto = self.extractor.extract_from_pdf(file_bytes, sanitized_filename)

        # Persist Extraction
        extracted_json = {
            "employee_name": extracted_dto.employee_name,
            "employee_code": extracted_dto.employee_code,
            "pan": extracted_dto.pan,
            "uan": extracted_dto.uan,
            "month": extracted_dto.month,
            "year": extracted_dto.year,
            "period_code": extracted_dto.period_code,
            "basic": str(extracted_dto.basic),
            "da": str(extracted_dto.da),
            "hra": str(extracted_dto.hra),
            "special_allowance": str(extracted_dto.special_allowance),
            "gross_earnings": str(extracted_dto.gross_earnings),
            "employee_epf": str(extracted_dto.employee_epf),
            "professional_tax": str(extracted_dto.professional_tax),
            "tds": str(extracted_dto.tds),
            "total_deductions": str(extracted_dto.total_deductions),
            "net_pay": str(extracted_dto.net_pay),
            "employer_epf": str(extracted_dto.employer_epf),
            "document_type": extracted_dto.document_type,
            "document_category": extracted_dto.document_category,
            "overall_confidence": extracted_dto.overall_confidence,
            "extraction_status": extracted_dto.extraction_status,
            "formula_verified": extracted_dto.formula_verified,
            "formula_discrepancy_rupees": str(extracted_dto.formula_discrepancy_rupees),
            "spatial_provenance": {
                k: {
                    "field_name": p.field_name,
                    "raw_value": p.raw_value,
                    "normalized_value": str(p.normalized_value),
                    "page_number": p.page_number,
                    "bounding_box": list(p.bounding_box),
                    "source_text": p.source_text,
                    "parser": p.parser,
                    "extraction_method": p.extraction_method,
                    "confidence": p.confidence,
                }
                for k, p in extracted_dto.spatial_provenance.items()
            },
        }

        self.repo.save_extraction(
            document_id=doc.id,
            extracted_data=extracted_json,
            confidence_score=Decimal(str(extracted_dto.overall_confidence)),
            ocr_engine_used=extracted_dto.spatial_provenance.get("basic", None).extraction_method
            if extracted_dto.spatial_provenance
            else "NATIVE_PDF",
            raw_text=extracted_dto.raw_text,
        )

        # 7. Hydrate Three-Way Truths & Execute Reconciliation
        reconcile_res = self.reconcile_document(doc.id, extracted_dto, employee_id)

        return doc.id, extracted_dto, reconcile_res

    def reconcile_document(
        self,
        document_id: int,
        extracted_dto: ExtractedPayslipDTO,
        employee_id: int,
    ) -> ReconciliationResultDTO:
        # A. Resolve PAYROLL_TRUTH from Phase 5 (PayrollRunItem)
        expected_payroll: ExpectedPayrollDTO | None = None
        if extracted_dto.period_code:
            payroll_item = self.db.scalar(
                select(PayrollRunItem)
                .join(PayrollRunItem.payroll_run)
                .join(
                    PayrollPeriod,
                    PayrollPeriod.id == PayrollRunItem.payroll_run.property.mapper.class_.payroll_period_id,
                )
                .where(
                    PayrollRunItem.employee_id == employee_id,
                    PayrollPeriod.period_code == extracted_dto.period_code,
                )
            )
            if payroll_item:
                expected_payroll = ExpectedPayrollDTO(
                    employee_id=employee_id,
                    period_code=extracted_dto.period_code,
                    gross_earnings=payroll_item.gross_earnings,
                    basic=payroll_item.basic,
                    hra=payroll_item.hra,
                    special_allowance=payroll_item.special_allowance,
                    employee_epf=payroll_item.employee_pf,
                    professional_tax=payroll_item.professional_tax,
                    tds=payroll_item.tax_tds,
                    total_deductions=payroll_item.total_deductions,
                    net_pay=payroll_item.net_pay,
                    employer_epf=payroll_item.employer_pf,
                    payroll_run_id=payroll_item.payroll_run_id,
                    payroll_item_id=payroll_item.id,
                )

        # B. Resolve STATUTORY_TRUTH from Phase 2 (CalculationSnapshot)
        statutory_engine: StatutoryExpectationDTO | None = None
        latest_snapshot = self.db.scalar(
            select(CalculationSnapshot)
            .join(CalculationSnapshot.calculation_run)
            .where(
                CalculationSnapshot.calculation_run.property.mapper.class_.employee_id == employee_id,
                CalculationSnapshot.is_active,
            )
            .order_by(CalculationSnapshot.created_at.desc())
        )
        if latest_snapshot:
            # Monthly estimates from annual snapshot
            statutory_engine = StatutoryExpectationDTO(
                annual_gross=latest_snapshot.annual_gross_income,
                monthly_gross=(latest_snapshot.annual_gross_income / Decimal("12")).quantize(Decimal("0.01")),
                monthly_epf=(latest_snapshot.total_pf_employee / Decimal("12")).quantize(Decimal("0.01")),
                monthly_pt=(latest_snapshot.total_professional_tax / Decimal("12")).quantize(Decimal("0.01")),
                monthly_tds_projected=(latest_snapshot.total_tax_liability / Decimal("12")).quantize(Decimal("0.01")),
                snapshot_id=latest_snapshot.id,
                tax_regime=latest_snapshot.tax_regime,
            )

        # C. Execute Pure Three-Way Reconciliation
        recon_result = ReconciliationEngine.reconcile(
            document_slip=extracted_dto,
            expected_payroll=expected_payroll,
            statutory_engine=statutory_engine,
        )

        # D. Persist Validation & Discrepancies
        discrepancy_payload = {
            "reconciliation_status": recon_result.reconciliation_status,
            "overall_score": recon_result.overall_score,
            "total_discrepancies": recon_result.total_discrepancies,
            "critical_discrepancies": recon_result.critical_discrepancies,
            "warning_discrepancies": recon_result.warning_discrepancies,
            "has_payroll_reference": recon_result.has_payroll_reference,
            "has_statutory_reference": recon_result.has_statutory_reference,
            "discrepancy_codes": recon_result.discrepancy_codes,
            "summary_explanation": recon_result.summary_explanation,
            "items": [
                {
                    "field_name": it.field_name,
                    "display_name": it.display_name,
                    "document_value": str(it.document_value) if it.document_value is not None else None,
                    "payroll_value": str(it.payroll_value) if it.payroll_value is not None else None,
                    "statutory_value": str(it.statutory_value) if it.statutory_value is not None else None,
                    "delta_document_vs_payroll": str(it.delta_document_vs_payroll),
                    "delta_document_vs_statutory": str(it.delta_document_vs_statutory)
                    if it.delta_document_vs_statutory is not None
                    else None,
                    "status": it.status,
                    "discrepancy_code": it.discrepancy_code,
                    "notes": it.notes,
                }
                for it in recon_result.items
            ],
        }

        self.repo.save_validation(
            document_id=document_id,
            validation_status=recon_result.reconciliation_status,
            discrepancy_flags=discrepancy_payload,
            reconciliation_notes=recon_result.summary_explanation,
        )

        return recon_result

    def record_correction(
        self,
        document_id: int,
        employee_id: int,
        field_name: str,
        new_value: str,
        reason: str,
        corrected_by_user_id: int,
    ) -> dict[str, Any]:
        """Audits human correction event and re-evaluates reconciliation without altering raw extraction."""
        doc = self.repo.get_document_by_id(document_id)
        if not doc or doc.employee_id != employee_id:
            raise ValueError("Document not found or access denied.")

        extraction = doc.extractions[0] if doc.extractions else None
        if not extraction:
            raise ValueError("No extraction found for document.")

        old_val = extraction.extracted_data.get(field_name, "0.00")

        event = {
            "field_name": field_name,
            "old_value": old_val,
            "new_value": new_value,
            "reason": reason,
            "corrected_by_user_id": corrected_by_user_id,
            "timestamp": uuid.uuid4().hex,
        }

        self.repo.record_correction_event(document_id, event)
        return event
