from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class PFRuleVersion(Base, TimestampMixin):
    __tablename__ = "pf_rule_versions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    version_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # e.g., 'EPFO_FY2024_25_v1'
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)

    rules: Mapped[list["PFRule"]] = relationship("PFRule", back_populates="rule_version", cascade="all, delete-orphan")
    interest_rules: Mapped[list["PFInterestRule"]] = relationship("PFInterestRule", back_populates="rule_version", cascade="all, delete-orphan")


class PFRule(Base, TimestampMixin):
    """
    Statutory PF Contribution Rules (EPF employee, EPF employer, EPS employer, EDLI, Admin charges, wage ceilings).
    Deliberately separated from PF interest rate rules.
    """
    __tablename__ = "pf_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pf_rule_version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("pf_rule_versions.id", ondelete="CASCADE"), nullable=False)

    employee_epf_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0.1200"), nullable=False)  # 12%
    employer_epf_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0.0367"), nullable=False)  # 3.67%
    employer_eps_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0.0833"), nullable=False)  # 8.33%
    employer_edli_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0.0050"), nullable=False)  # 0.50%
    admin_charges_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0.0050"), nullable=False)  # 0.50%

    statutory_wage_ceiling: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("15000.00"), nullable=False)
    eps_wage_ceiling: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("15000.00"), nullable=False)
    vpf_allowed: Mapped[bool] = mapped_column(default=True, nullable=False)

    rule_version: Mapped["PFRuleVersion"] = relationship("PFRuleVersion", back_populates="rules")


class PFInterestRule(Base, TimestampMixin):
    """
    Statutory PF Annual Interest Rates for balances and multi-year projection.
    Deliberately separated from PF contribution parameters.
    """
    __tablename__ = "pf_interest_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pf_rule_version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("pf_rule_versions.id", ondelete="CASCADE"), nullable=False)
    financial_year: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., '2024-25'
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)  # e.g., 0.0825 for 8.25%
    notification_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    rule_version: Mapped["PFRuleVersion"] = relationship("PFRuleVersion", back_populates="interest_rules")
