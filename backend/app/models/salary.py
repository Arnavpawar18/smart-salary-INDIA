from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee


class IncomeSource(Base, TimestampMixin):
    __tablename__ = "income_sources"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    # Category: SALARY (MVP), future extensibility: INTEREST, HOUSE_PROPERTY, CAPITAL_GAINS, OTHER_SOURCES
    source_type: Mapped[str] = mapped_column(String(50), default="SALARY", nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    annual_gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    financial_year: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., '2024-25'
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="income_sources")


class SalaryRecord(Base, TimestampMixin):
    __tablename__ = "salary_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    annual_ctc: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    monthly_gross: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="salary_records")
    components: Mapped[list["SalaryComponent"]] = relationship("SalaryComponent", back_populates="salary_record", cascade="all, delete-orphan")


class SalaryComponent(Base, TimestampMixin):
    __tablename__ = "salary_components"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    salary_record_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("salary_records.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., Basic, HRA, Special Allowance
    component_type: Mapped[str] = mapped_column(String(50), nullable=False)  # EARNING, DEDUCTION, REIMBURSEMENT
    monthly_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    annual_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    is_taxable: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_pf_applicable: Mapped[bool] = mapped_column(default=False, nullable=False)

    salary_record: Mapped["SalaryRecord"] = relationship("SalaryRecord", back_populates="components")
