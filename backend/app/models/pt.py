from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import State


class ProfessionalTaxRuleVersion(Base, TimestampMixin):
    __tablename__ = "professional_tax_rule_versions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    state_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("states.id"), nullable=False)
    version_code: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'PT_MH_FY2024_25_v1'
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)

    state: Mapped["State"] = relationship("State")
    slabs: Mapped[list["ProfessionalTaxSlab"]] = relationship("ProfessionalTaxSlab", back_populates="rule_version", cascade="all, delete-orphan")


class ProfessionalTaxSlab(Base, TimestampMixin):
    __tablename__ = "professional_tax_slabs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pt_rule_version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("professional_tax_rule_versions.id", ondelete="CASCADE"), nullable=False)
    slab_order: Mapped[int] = mapped_column(nullable=False)
    from_monthly_salary: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    to_monthly_salary: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)  # NULL for upper bound
    monthly_tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    february_tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)  # Special rate for Feb (e.g., MH: Rs 300)
    gender_applicable: Mapped[str] = mapped_column(String(20), default="ALL", nullable=False)  # ALL, MALE, FEMALE

    rule_version: Mapped["ProfessionalTaxRuleVersion"] = relationship("ProfessionalTaxRuleVersion", back_populates="slabs")
