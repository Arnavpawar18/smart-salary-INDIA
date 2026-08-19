from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.auth_middleware import CSRFProtection, get_current_user
from app.core.database import get_db
from app.core.rate_limiter import InMemoryRateLimiter
from app.models.auth import User
from app.schemas.payslip import (
    CorrectionRequest,
    PayslipDocumentSummarySchema,
)
from app.services.audit_service import AuditEvent, AuditService
from app.services.payslip_service import PayslipService

router = APIRouter()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_payslip(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Secure Payslip PDF Upload Endpoint:
    - Enforces sliding-window rate limiting.
    - Validates CSRF token for state mutation.
    - Enforces strict employee object binding (user must have employee profile).
    - Executes Document Security Pipeline (Validation, Quarantine, Scan, Extraction, 3-Way Reconciliation).
    """
    # 1. Rate Limiter (Max 10 uploads per minute per IP)
    client_ip = InMemoryRateLimiter.get_client_ip(request)
    InMemoryRateLimiter.check_rate_limit(f"payslip_upload_{client_ip}", max_requests=10, window_seconds=60)

    # 2. CSRF Validation
    CSRFProtection.validate_request(request)

    # 3. Authorization Check: Current user must have linked employee_id
    if not current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user has no associated Employee profile. Upload not permitted.",
        )

    # 4. Read File Bytes
    file_bytes = await file.read()

    service = PayslipService(db)
    try:
        doc_id, extracted_dto, recon_result = service.process_payslip_upload(
            employee_id=current_user.employee_id,
            file_bytes=file_bytes,
            original_filename=file.filename or "payslip.pdf",
            uploaded_by_user_id=current_user.id,
        )

        AuditService.log_event(
            db=db,
            user_id=current_user.id,
            event_type=AuditEvent.CALCULATION_SAVED,  # Audit payslip processing
            entity_type="PayslipDocument",
            entity_id=doc_id,
            details={
                "action": "PAYSLIP_UPLOAD_AND_RECONCILE",
                "filename": file.filename,
                "reconciliation_status": recon_result.reconciliation_status,
                "score": recon_result.overall_score,
            },
        )
        db.commit()

        return {
            "document_id": doc_id,
            "status": "PROCESSED",
            "extraction": {
                "employee_name": extracted_dto.employee_name,
                "pan": extracted_dto.pan,
                "month": extracted_dto.month,
                "year": extracted_dto.year,
                "period_code": extracted_dto.period_code,
                "gross_earnings": str(extracted_dto.gross_earnings),
                "total_deductions": str(extracted_dto.total_deductions),
                "net_pay": str(extracted_dto.net_pay),
                "overall_confidence": extracted_dto.overall_confidence,
                "extraction_status": extracted_dto.extraction_status,
                "formula_verified": extracted_dto.formula_verified,
            },
            "reconciliation": {
                "status": recon_result.reconciliation_status,
                "overall_score": recon_result.overall_score,
                "critical_discrepancies": recon_result.critical_discrepancies,
                "warning_discrepancies": recon_result.warning_discrepancies,
                "discrepancy_codes": recon_result.discrepancy_codes,
                "summary": recon_result.summary_explanation,
            },
        }

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing payslip: {str(e)}",
        )


@router.get("", response_model=list[PayslipDocumentSummarySchema])
def list_payslips(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists all payslips uploaded by the authenticated employee."""
    if not current_user.employee_id:
        return []

    service = PayslipService(db)
    docs = service.repo.list_employee_documents(current_user.employee_id)

    results = []
    for d in docs:
        recon_status = d.validations[0].validation_status if d.validations else "UNRECONCILED"
        period_code = None
        if d.extractions and d.extractions[0].extracted_data:
            period_code = d.extractions[0].extracted_data.get("period_code")

        results.append(
            PayslipDocumentSummarySchema(
                id=d.id,
                employee_id=d.employee_id,
                file_name=d.file_name,
                file_size_bytes=d.file_size_bytes,
                file_hash=d.file_hash,
                status=d.status,
                period_code=period_code,
                reconciliation_status=recon_status,
                created_at=d.created_at,
            )
        )
    return results


@router.get("/{document_id}")
def get_payslip_details(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetches full extraction data, spatial provenance, and 3-way reconciliation items.
    Enforces strict IDOR defense (User can only view their own documents unless HR/Admin).
    """
    service = PayslipService(db)
    doc = service.repo.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payslip document not found.")

    # IDOR Defense
    user_roles = [r.name for r in current_user.roles]
    is_admin_or_hr = any(r in ["SUPER_ADMIN", "ADMIN", "HR_MANAGER", "PAYROLL_ADMIN"] for r in user_roles)
    if not is_admin_or_hr and doc.employee_id != current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to view this payslip.",
        )

    extraction = doc.extractions[0] if doc.extractions else None
    validation = doc.validations[0] if doc.validations else None

    return {
        "id": doc.id,
        "employee_id": doc.employee_id,
        "file_name": doc.file_name,
        "file_size_bytes": doc.file_size_bytes,
        "file_hash": doc.file_hash,
        "status": doc.status,
        "created_at": doc.created_at,
        "extraction": extraction.extracted_data if extraction else None,
        "raw_text": extraction.raw_text if extraction else None,
        "confidence_score": str(extraction.confidence_score) if extraction else None,
        "validation": validation.discrepancy_flags if validation else None,
        "reconciliation_status": validation.validation_status if validation else "UNRECONCILED",
    }


@router.post("/{document_id}/corrections")
def record_correction(
    document_id: int,
    req: CorrectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Records an audited human correction event without altering raw document extraction.
    """
    service = PayslipService(db)
    doc = service.repo.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payslip document not found.")

    # IDOR Defense
    user_roles = [r.name for r in current_user.roles]
    is_admin_or_hr = any(r in ["SUPER_ADMIN", "ADMIN", "HR_MANAGER", "PAYROLL_ADMIN"] for r in user_roles)
    if not is_admin_or_hr and doc.employee_id != current_user.employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden.")

    try:
        event = service.record_correction(
            document_id=document_id,
            employee_id=doc.employee_id,
            field_name=req.field_name,
            new_value=req.new_value,
            reason=req.reason,
            corrected_by_user_id=current_user.id,
        )
        db.commit()
        return {"status": "SUCCESS", "correction": event}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
