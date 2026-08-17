from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.calculation import CalculationRun, CalculationSnapshot
    from app.models.employee import Employee
    from app.models.organization import Organization


class PayrollPeriod(Base, TimestampMixin):
    """
    Monthly enterprise payroll processing cycle (e.g. FY 2026-27 period '2026-04').
    Statuses: OPEN, INPUT_COLLECTION, CALCULATING, CALCULATED, UNDER_REVIEW, APPROVED, PROCESSING, PROCESSED, LOCKED, CLOSED, REOPEN_REQUESTED, REOPENED
    """
    __tablename__ = "payroll_periods"
    __table_args__ = (
        UniqueConstraint("organization_id", "period_code", name="uq_payroll_period_org_code"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    financial_year: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # e.g., '2026-27'
    period_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)     # e.g., '2026-04'
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    pay_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="OPEN", nullable=False, index=True)

    # Lifecycle & Audit timestamps
    calculated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    payroll_runs: Mapped[list["PayrollRun"]] = relationship("PayrollRun", back_populates="payroll_period", cascade="all, delete-orphan")


class PayrollRun(Base, TimestampMixin):
    """
    Authoritative Payroll Run for an organization & period.
    Idempotency key: (organization_id, payroll_period_id, run_version)
    """
    __tablename__ = "payroll_runs"
    __table_args__ = (
        UniqueConstraint("organization_id", "payroll_period_id", "run_version", name="uq_payroll_run_idempotency"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    payroll_period_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("payroll_periods.id", ondelete="CASCADE"), nullable=False, index=True)
    run_version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", nullable=False, index=True)  # DRAFT, CALCULATED, HR_REVIEW, APPROVED, LOCKED

    # Aggregated Financial Totals (Verified against sum of run items)
    total_gross_earnings: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    total_employee_deductions: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    total_tax_tds: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    total_employee_pf: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    total_employer_pf: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    total_pt: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    total_net_pay: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    total_employer_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)

    # Cryptographic Provenance & Maker/Checker
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(50), default="CALC-1.0.0", nullable=False)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    payroll_period: Mapped["PayrollPeriod"] = relationship("PayrollPeriod", back_populates="payroll_runs")
    items: Mapped[list["PayrollRunItem"]] = relationship("PayrollRunItem", back_populates="payroll_run", cascade="all, delete-orphan")


class PayrollRunItem(Base, TimestampMixin):
    """
    Individual employee payroll line item.
    Directly links to Phase 2 CalculationRun and CalculationSnapshot.
    """
    __tablename__ = "payroll_run_items"
    __table_args__ = (
        UniqueConstraint("payroll_run_id", "employee_id", name="uq_payroll_item_emp"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    payroll_run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    calculation_run_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("calculation_runs.id"), nullable=True)
    calculation_snapshot_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("calculation_snapshots.id"), nullable=True)

    # Canonical 3-View Accounting Breakdown
    monthly_gross: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    basic_salary: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    hra: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    special_allowance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    other_earnings: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)

    # Employee Deductions
    employee_pf: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    professional_tax: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    tds_deducted: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    other_deductions: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    total_employee_deductions: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # Net Take-Home
    net_pay: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # Employer Contributions (Never deducted from employee net pay)
    employer_pf: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    employer_eps: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    employer_edli: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    employer_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # Attendance/Inputs metadata
    days_worked: Mapped[int] = mapped_column(default=30, nullable=False)
    lop_days: Mapped[int] = mapped_column(default=0, nullable=False)

    # Relationships
    payroll_run: Mapped["PayrollRun"] = relationship("PayrollRun", back_populates="items")
    employee: Mapped["Employee"] = relationship("Employee")
    calculation_run: Mapped[Optional["CalculationRun"]] = relationship("CalculationRun")
    calculation_snapshot: Mapped[Optional["CalculationSnapshot"]] = relationship("CalculationSnapshot")
