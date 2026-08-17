from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import BigInteger, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee


class CalculationRun(Base, TimestampMixin):
    __tablename__ = "calculation_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    employee_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("employees.id", ondelete="CASCADE"), nullable=True)
    financial_year: Mapped[str] = mapped_column(String(20), nullable=False)  # '2024-25', etc.
    regime: Mapped[str] = mapped_column(String(10), nullable=False)  # OLD, NEW
    status: Mapped[str] = mapped_column(String(50), default="COMPLETED", nullable=False)
    total_taxable_income: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    total_tax_liability: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    net_take_home_annual: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    net_take_home_monthly: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="calculation_runs")

    # 1..1 with CalculationSnapshot (enforced via UNIQUE NOT NULL FK on calculation_snapshots.calculation_run_id)
    snapshot: Mapped[Optional["CalculationSnapshot"]] = relationship("CalculationSnapshot", back_populates="calculation_run", uselist=False)
    traces: Mapped[list["CalculationTrace"]] = relationship("CalculationTrace", back_populates="calculation_run", cascade="all, delete-orphan")
    line_items: Mapped[list["CalculationLineItem"]] = relationship("CalculationLineItem", back_populates="calculation_run", cascade="all, delete-orphan")


class CalculationSnapshot(Base, TimestampMixin):
    """
    Immutable historical calculation snapshot (CREATE + READ only).
    Preserves exact input/result JSONB snapshots, hashes, and foreign keys to rule versions.
    """
    __tablename__ = "calculation_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Enforce strict 1..1 with CalculationRun at DB level (UNIQUE + NOT NULL)
    calculation_run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("calculation_runs.id", ondelete="CASCADE"), unique=True, nullable=False)

    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # Canonical SHA-256
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # Canonical SHA-256
    engine_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)

    # Referential integrity to rule versions
    tax_rule_version_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("tax_rule_versions.id"), nullable=True)
    pf_rule_version_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("pf_rule_versions.id"), nullable=True)
    professional_tax_rule_version_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("professional_tax_rule_versions.id"), nullable=True)
    rounding_policy_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)

    calculation_run: Mapped["CalculationRun"] = relationship("CalculationRun", back_populates="snapshot")


class CalculationLineItem(Base, TimestampMixin):
    __tablename__ = "calculation_line_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    calculation_run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("calculation_runs.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # GROSS, EXEMPTION, DEDUCTION, TAX_SLAB, REBATE, CESS
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'BASIC', '80C', 'SLAB_1'
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    order_index: Mapped[int] = mapped_column(default=0, nullable=False)

    calculation_run: Mapped["CalculationRun"] = relationship("CalculationRun", back_populates="line_items")
    traces: Mapped[list["CalculationTrace"]] = relationship("CalculationTrace", back_populates="source_line_item")


class CalculationTrace(Base, TimestampMixin):
    __tablename__ = "calculation_traces"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    calculation_run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("calculation_runs.id", ondelete="CASCADE"), nullable=False)
    # Trace step referential integrity to CalculationLineItem (nullable if not tied to single item)
    source_line_item_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("calculation_line_items.id", ondelete="SET NULL"), nullable=True)
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    formula_expression: Mapped[str | None] = mapped_column(Text, nullable=True)
    inputs_applied: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    output_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    calculation_run: Mapped["CalculationRun"] = relationship("CalculationRun", back_populates="traces")
    source_line_item: Mapped[Optional["CalculationLineItem"]] = relationship("CalculationLineItem", back_populates="traces")
