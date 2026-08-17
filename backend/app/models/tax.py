from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TaxPeriod(Base, TimestampMixin):
    __tablename__ = "tax_periods"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    financial_year: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)  # e.g., '2024-25'
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    legacy_assessment_year: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., '2025-26'
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    rule_versions: Mapped[list["TaxRuleVersion"]] = relationship("TaxRuleVersion", back_populates="tax_period")


class TaxRuleVersion(Base, TimestampMixin):
    __tablename__ = "tax_rule_versions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tax_period_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tax_periods.id"), nullable=False)
    version_code: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'v2024_25_new_v1'
    regime: Mapped[str] = mapped_column(String(10), nullable=False)  # OLD, NEW
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)  # DRAFT, ACTIVE, SUPERSEDED

    tax_period: Mapped["TaxPeriod"] = relationship("TaxPeriod", back_populates="rule_versions")
    slabs: Mapped[list["TaxSlab"]] = relationship("TaxSlab", back_populates="rule_version", cascade="all, delete-orphan")
    rebates: Mapped[list["TaxRebate"]] = relationship("TaxRebate", back_populates="rule_version", cascade="all, delete-orphan")
    exemptions: Mapped[list["TaxExemption"]] = relationship("TaxExemption", back_populates="rule_version", cascade="all, delete-orphan")
    deductions: Mapped[list["TaxDeduction"]] = relationship("TaxDeduction", back_populates="rule_version", cascade="all, delete-orphan")
    surcharges: Mapped[list["TaxSurcharge"]] = relationship("TaxSurcharge", back_populates="rule_version", cascade="all, delete-orphan")
    cess_rules: Mapped[list["TaxCessRule"]] = relationship("TaxCessRule", back_populates="rule_version", cascade="all, delete-orphan")
    sources: Mapped[list["TaxSource"]] = relationship("TaxSource", back_populates="rule_version", cascade="all, delete-orphan")


class TaxSlab(Base, TimestampMixin):
    __tablename__ = "tax_slabs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tax_rule_version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tax_rule_versions.id", ondelete="CASCADE"), nullable=False)
    slab_order: Mapped[int] = mapped_column(nullable=False)
    from_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    to_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)  # NULL for infinite bracket
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)  # e.g., 0.0500 for 5%

    rule_version: Mapped["TaxRuleVersion"] = relationship("TaxRuleVersion", back_populates="slabs")


class TaxRebate(Base, TimestampMixin):
    __tablename__ = "tax_rebates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tax_rule_version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tax_rule_versions.id", ondelete="CASCADE"), nullable=False)
    section: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., '87A'
    threshold_taxable_income: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    max_rebate_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    rule_version: Mapped["TaxRuleVersion"] = relationship("TaxRuleVersion", back_populates="rebates")


class TaxExemption(Base, TimestampMixin):
    __tablename__ = "tax_exemptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tax_rule_version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tax_rule_versions.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'HRA', 'STANDARD_DEDUCTION', 'LTA'
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    max_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    rule_version: Mapped["TaxRuleVersion"] = relationship("TaxRuleVersion", back_populates="exemptions")


class TaxDeduction(Base, TimestampMixin):
    __tablename__ = "tax_deductions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tax_rule_version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tax_rule_versions.id", ondelete="CASCADE"), nullable=False)
    section: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., '80C', '80D', '80CCD(1B)'
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    max_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    rule_version: Mapped["TaxRuleVersion"] = relationship("TaxRuleVersion", back_populates="deductions")


class TaxSurcharge(Base, TimestampMixin):
    __tablename__ = "tax_surcharges"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tax_rule_version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tax_rule_versions.id", ondelete="CASCADE"), nullable=False)
    from_income: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    to_income: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    surcharge_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)  # e.g., 0.1000 for 10%
    is_marginal_relief_applicable: Mapped[bool] = mapped_column(default=True, nullable=False)

    rule_version: Mapped["TaxRuleVersion"] = relationship("TaxRuleVersion", back_populates="surcharges")


class TaxCessRule(Base, TimestampMixin):
    __tablename__ = "tax_cess_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tax_rule_version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tax_rule_versions.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), default="Health and Education Cess", nullable=False)
    cess_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)  # e.g., 0.0400 for 4%

    rule_version: Mapped["TaxRuleVersion"] = relationship("TaxRuleVersion", back_populates="cess_rules")


class TaxSource(Base, TimestampMixin):
    __tablename__ = "tax_sources"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tax_rule_version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tax_rule_versions.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g., 'Finance Act 2024'
    authority: Mapped[str] = mapped_column(String(100), default="CBDT / Ministry of Finance", nullable=False)
    reference_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    rule_version: Mapped["TaxRuleVersion"] = relationship("TaxRuleVersion", back_populates="sources")
