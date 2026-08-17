from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.organization import Organization


class TaxDeclaration(Base, TimestampMixin):
    """
    Employee tax declarations (Section 80C, 80D, 24b Home Loan, HRA, NPS 80CCD, etc.)
    Lifecycle Stages (6-Stage Compliance):
    1. DRAFT: Employee editing
    2. SUBMITTED: Submitted with planned declaration amounts
    3. UNDER_REVIEW: Payroll/HR checking compliance
    4. VERIFIED: Proofs inspected and accepted
    5. REJECTED: Resubmission requested with reason
    6. FROZEN: Locked for annual tax finalization
    """
    __tablename__ = "tax_declarations"
    __table_args__ = (
        UniqueConstraint("employee_id", "financial_year", "regime", name="uq_tax_declaration_emp_fy_regime"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    financial_year: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    regime: Mapped[str] = mapped_column(String(10), default="NEW", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", nullable=False, index=True)  # DRAFT, SUBMITTED, UNDER_REVIEW, VERIFIED, REJECTED, FROZEN

    # Aggregated Declared vs Verified Totals
    total_declared_deductions: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    total_verified_deductions: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)

    # 3-Tier TDS Tracking
    projected_annual_liability: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    planned_monthly_withholding: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    actual_tds_deducted_ytd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)

    # Audit & Approval
    submitted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    verified_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    employee: Mapped["Employee"] = relationship("Employee")
    organization: Mapped["Organization"] = relationship("Organization")
    items: Mapped[list["TaxDeclarationItem"]] = relationship("TaxDeclarationItem", back_populates="declaration", cascade="all, delete-orphan")


class TaxDeclarationItem(Base, TimestampMixin):
    """
    Granular declaration line items (e.g. 80C PPF, 80D Mediclaim, HRA rent paid).
    """
    __tablename__ = "tax_declaration_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    declaration_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tax_declarations.id", ondelete="CASCADE"), nullable=False, index=True)
    section_code: Mapped[str] = mapped_column(String(50), nullable=False)  # 80C, 80D, 80CCD_1B, 24B, HRA_RENT
    category_name: Mapped[str] = mapped_column(String(100), nullable=False)  # 'Public Provident Fund', 'Life Insurance Premium'
    declared_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    verified_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)  # PENDING, ACCEPTED, REJECTED
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    declaration: Mapped["TaxDeclaration"] = relationship("TaxDeclaration", back_populates="items")


class StatutoryComplianceEvent(Base, TimestampMixin):
    """
    Immutable compliance calendar tracking (e.g. Form 24Q Quarterly Return, PF ECR Filing, PT Remittance).
    """
    __tablename__ = "statutory_compliance_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # TDS_DEPOSIT, FORM_24Q, PF_ECR, PT_RETURN, FORM_16_ISSUE
    financial_year: Mapped[str] = mapped_column(String(20), nullable=False)
    period_label: Mapped[str] = mapped_column(String(50), nullable=False)  # 'Q1 (Apr-Jun)', 'Monthly Apr 2026'
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)  # PENDING, IN_PROGRESS, FILED, DELAYED, RECONCILED
    acknowledgement_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    meta_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    organization: Mapped["Organization"] = relationship("Organization")
