from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

# ── Common Enums & Models ───────────────────────────────────────────────────

class DepartmentHeatmapItem(BaseModel):
    department: str
    risk: Literal["Low", "Medium", "High", "Critical", "Very Low"]
    score: int


class AnomalyItem(BaseModel):
    id: int
    type: str
    severity: Literal["CRITICAL", "WARNING", "NOTICE"]
    title: str
    description: str
    department: str | None = None
    status: str = "OPEN"
    timestamp: str


class AIInsightsPayload(BaseModel):
    version: str = "v4.2"
    summary: str
    supporting_evidence: str
    recommendation: str


# ── Risk Engine ─────────────────────────────────────────────────────────────

class RiskMetricsResponse(BaseModel):
    risk_index: int = Field(..., ge=0, le=100)
    risk_level: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
    vs_last_month: str
    anomalies: list[AnomalyItem]
    department_heatmap: list[DepartmentHeatmapItem]
    ai_insights: AIInsightsPayload


# ── Tax Analytics ───────────────────────────────────────────────────────────

class DeductionBreakdownItem(BaseModel):
    name: str
    percentage: int
    amount: Decimal


class DepartmentComplianceRow(BaseModel):
    department: str
    headcount: int
    compliance_percentage: int
    status: Literal["EXCELLENT", "GOOD", "WARNING", "CRITICAL"]


class TaxAnalyticsResponse(BaseModel):
    total_tax_liability_ytd: Decimal
    avg_employee_tax_saving: Decimal
    compliance_rate: Decimal
    projected_ai_savings: Decimal
    monthly_trend: list[dict[str, Any]]
    deduction_distribution: list[DeductionBreakdownItem]
    departmental_compliance: list[DepartmentComplianceRow]
    ai_insights: list[dict[str, str]]


# ── Compliance Reports ──────────────────────────────────────────────────────

class ComplianceReportItem(BaseModel):
    id: int
    report_name: str
    report_type: str
    period: str
    generated_at: str
    generated_by: str
    status: Literal["READY", "GENERATING", "FAILED", "EXPIRED"]
    download_url: str | None = None


class GenerateComplianceReportRequest(BaseModel):
    report_type: str = Field(..., description="TDS, INVESTMENT_PROOF, PAYROLL_RECON, PF_ESI_RETURNS")
    financial_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    period: str = Field(..., description="Q1, Q2, Q3, Q4, ANNUAL, or MONTHLY")
    include_raw_ledger: bool = False


# ── Approvals Workflow ──────────────────────────────────────────────────────

class ApprovalRequestItem(BaseModel):
    id: int
    employee_name: str
    employee_code: str
    request_type: str
    submitted_on: str
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    amount_declared: Decimal
    status: Literal["PENDING", "UNDER_REVIEW", "APPROVED", "REJECTED", "CLARIFICATION_REQUIRED"]
    document_name: str | None = None
    document_url: str | None = None


class ApprovalActionRequest(BaseModel):
    action: Literal["APPROVE", "REJECT", "CLARIFICATION_REQUIRED"]
    remarks: str | None = None
    verified_amount: Decimal | None = None


# ── Audit Logs ──────────────────────────────────────────────────────────────

class AuditLogRow(BaseModel):
    id: int
    timestamp_ist: str
    actor_name: str
    actor_type: str
    action: str
    target_type: str
    target_id: int | None
    category: str
    ip_address: str | None
    status: str = "SUCCESS"


# ── Employee Self-Service ───────────────────────────────────────────────────

class EmployeeSectionProgress(BaseModel):
    declared: Decimal
    verified: Decimal
    statutory_limit: Decimal
    breakdown: list[dict[str, Any]]


class EmployeeTaxCenterResponse(BaseModel):
    financial_year: str
    selected_regime: str
    old_regime_tax: Decimal
    new_regime_tax: Decimal
    tax_savings_optimal: Decimal
    recommended_regime: str
    sections: dict[str, EmployeeSectionProgress]
    ai_recommendations: list[dict[str, str]]


class EmployeeDeclarationSubmission(BaseModel):
    financial_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    regime: Literal["OLD", "NEW"]
    items: list[dict[str, Any]]
