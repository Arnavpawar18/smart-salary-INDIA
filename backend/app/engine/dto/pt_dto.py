from dataclasses import dataclass
from decimal import Decimal

from app.engine.common.enums import Gender


@dataclass(frozen=True)
class PtCalculationInput:
    state_code: str
    monthly_gross_salary: Decimal
    gender: Gender = Gender.ALL


@dataclass(frozen=True)
class PtSlabRuleDTO:
    slab_order: int
    from_monthly_salary: Decimal
    to_monthly_salary: Decimal | None
    monthly_tax_amount: Decimal
    february_tax_amount: Decimal | None
    gender_applicable: Gender


@dataclass(frozen=True)
class PtRuleSet:
    state_code: str
    state_name: str
    rule_version_code: str
    slabs: list[PtSlabRuleDTO]
    source_citation: str
    source_document_hash: str
    rule_set_hash: str

    def to_dict(self) -> dict:
        return {
            "state_code": self.state_code,
            "state_name": self.state_name,
            "rule_version_code": self.rule_version_code,
            "source_citation": self.source_citation,
            "rule_set_hash": self.rule_set_hash,
            "slabs": [
                {
                    "slab_order": s.slab_order,
                    "from_monthly_salary": f"{s.from_monthly_salary:.2f}",
                    "to_monthly_salary": f"{s.to_monthly_salary:.2f}" if s.to_monthly_salary is not None else None,
                    "monthly_tax_amount": f"{s.monthly_tax_amount:.2f}",
                    "february_tax_amount": f"{s.february_tax_amount:.2f}" if s.february_tax_amount is not None else None,
                }
                for s in self.slabs
            ],
        }


@dataclass(frozen=True)
class PtCalculationResult:
    state_code: str
    monthly_pt: Decimal
    february_pt: Decimal
    annual_pt: Decimal
    rule_version_code: str
