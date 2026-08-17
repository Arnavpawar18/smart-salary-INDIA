from dataclasses import dataclass
from decimal import Decimal

from app.engine.common.enums import ResidentialStatus, TaxRegime


@dataclass(frozen=True)
class TaxCalculationInput:
    """Input parameters passed to the pure Tax Engine."""
    financial_year: str
    regime: TaxRegime
    annual_gross_salary: Decimal
    age: int = 25
    residential_status: ResidentialStatus = ResidentialStatus.RESIDENT
    standard_deduction_override: Decimal | None = None
    section_80c: Decimal = Decimal("0.00")
    section_80d: Decimal = Decimal("0.00")
    other_exemptions: Decimal = Decimal("0.00")
    other_deductions: Decimal = Decimal("0.00")
    tds_already_deducted: Decimal | None = None


@dataclass(frozen=True)
class TaxSlabRuleDTO:
    slab_order: int
    from_amount: Decimal
    to_amount: Decimal | None
    tax_rate: Decimal


@dataclass(frozen=True)
class TaxRebateRuleDTO:
    section_code: str
    taxable_income_threshold: Decimal
    max_rebate_amount: Decimal
    marginal_relief_applicable: bool = True


@dataclass(frozen=True)
class TaxDeductionRuleDTO:
    deduction_code: str
    deduction_name: str
    max_limit: Decimal | None
    regime_applicable: str
    is_standard_deduction: bool = False


@dataclass(frozen=True)
class TaxSurchargeRuleDTO:
    from_income: Decimal
    to_income: Decimal | None
    surcharge_rate: Decimal
    marginal_relief_applicable: bool = True


@dataclass(frozen=True)
class TaxCessRuleDTO:
    cess_name: str
    cess_rate: Decimal


@dataclass(frozen=True)
class TaxRuleSet:
    """Immutable statutory tax rule set hydrated from database with source provenance."""
    rule_version_code: str
    financial_year: str
    regime: TaxRegime
    slabs: list[TaxSlabRuleDTO]
    rebates: list[TaxRebateRuleDTO]
    deductions: list[TaxDeductionRuleDTO]
    surcharges: list[TaxSurchargeRuleDTO]
    cess_rules: list[TaxCessRuleDTO]
    source_citation: str
    source_document_hash: str
    rule_set_hash: str

    def to_dict(self) -> dict:
        return {
            "rule_version_code": self.rule_version_code,
            "financial_year": self.financial_year,
            "regime": self.regime.value,
            "source_citation": self.source_citation,
            "source_document_hash": self.source_document_hash,
            "rule_set_hash": self.rule_set_hash,
            "slabs": [
                {
                    "slab_order": s.slab_order,
                    "from_amount": f"{s.from_amount:.2f}",
                    "to_amount": f"{s.to_amount:.2f}" if s.to_amount is not None else None,
                    "tax_rate": f"{s.tax_rate:.4f}",
                }
                for s in self.slabs
            ],
            "rebates": [
                {
                    "section_code": r.section_code,
                    "taxable_income_threshold": f"{r.taxable_income_threshold:.2f}",
                    "max_rebate_amount": f"{r.max_rebate_amount:.2f}",
                }
                for r in self.rebates
            ],
            "deductions": [
                {
                    "deduction_code": d.deduction_code,
                    "max_limit": f"{d.max_limit:.2f}" if d.max_limit is not None else None,
                }
                for d in self.deductions
            ],
            "cess_rules": [{"cess_name": c.cess_name, "cess_rate": f"{c.cess_rate:.4f}"} for c in self.cess_rules],
        }
