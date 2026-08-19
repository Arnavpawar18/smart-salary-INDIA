from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SpatialProvenanceSchema(BaseModel):
    field_name: str
    raw_value: str
    normalized_value: Any
    page_number: int
    bounding_box: tuple[float, float, float, float]
    source_text: str
    parser: str
    extraction_method: str
    confidence: float

    model_config = ConfigDict(from_attributes=True)


class ExtractedPayslipSchema(BaseModel):
    employee_name: str | None = None
    employee_code: str | None = None
    pan: str | None = None
    uan: str | None = None
    designation: str | None = None
    department: str | None = None
    organization_name: str | None = None

    month: str | None = None
    year: int | None = None
    period_code: str | None = None

    basic: Decimal = Decimal("0.00")
    da: Decimal = Decimal("0.00")
    hra: Decimal = Decimal("0.00")
    special_allowance: Decimal = Decimal("0.00")
    conveyance: Decimal = Decimal("0.00")
    transport: Decimal = Decimal("0.00")
    medical: Decimal = Decimal("0.00")
    bonus: Decimal = Decimal("0.00")
    incentive: Decimal = Decimal("0.00")
    overtime: Decimal = Decimal("0.00")
    arrears: Decimal = Decimal("0.00")
    other_earnings: Decimal = Decimal("0.00")
    gross_earnings: Decimal = Decimal("0.00")

    employee_epf: Decimal = Decimal("0.00")
    professional_tax: Decimal = Decimal("0.00")
    tds: Decimal = Decimal("0.00")
    esi: Decimal = Decimal("0.00")
    total_deductions: Decimal = Decimal("0.00")

    employer_epf: Decimal = Decimal("0.00")
    net_pay: Decimal = Decimal("0.00")

    document_type: str
    document_category: str
    overall_confidence: float
    extraction_status: str
    formula_verified: bool
    formula_discrepancy_rupees: Decimal = Decimal("0.00")
    spatial_provenance: dict[str, SpatialProvenanceSchema] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class FieldReconciliationItemSchema(BaseModel):
    field_name: str
    display_name: str
    document_value: Decimal | None = None
    payroll_value: Decimal | None = None
    statutory_value: Decimal | None = None
    delta_document_vs_payroll: Decimal = Decimal("0.00")
    delta_document_vs_statutory: Decimal | None = None
    status: str  # MATCHED, WARNING, CRITICAL, SKIPPED
    discrepancy_code: str | None = None
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ReconciliationResultSchema(BaseModel):
    reconciliation_status: str  # MATCHED, DISCREPANCY_WARNING, DISCREPANCY_CRITICAL, UNRECONCILED
    overall_score: float
    total_discrepancies: int
    critical_discrepancies: int
    warning_discrepancies: int
    has_payroll_reference: bool
    has_statutory_reference: bool
    formula_verified: bool
    items: list[FieldReconciliationItemSchema] = Field(default_factory=list)
    discrepancy_codes: list[str] = Field(default_factory=list)
    summary_explanation: str = ""

    model_config = ConfigDict(from_attributes=True)


class CorrectionEventSchema(BaseModel):
    field_name: str
    old_value: Any
    new_value: Any
    reason: str
    corrected_by_user_id: int
    corrected_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class CorrectionRequest(BaseModel):
    field_name: str
    new_value: str
    reason: str


class ReviewRequest(BaseModel):
    review_status: str  # REVIEWED, CORRECTED, FINALIZED
    notes: str | None = None


class PayslipDocumentSummarySchema(BaseModel):
    id: int
    employee_id: int
    file_name: str
    file_size_bytes: int
    file_hash: str
    status: str
    period_code: str | None = None
    reconciliation_status: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
