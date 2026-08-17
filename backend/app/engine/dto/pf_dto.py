from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class PfCalculationInput:
    pf_wage_base_monthly: Decimal
    is_pf_applicable: bool = True
    opt_in_higher_wage: bool = False


@dataclass(frozen=True)
class PfRuleSet:
    rule_version_code: str
    employee_epf_rate: Decimal
    employer_epf_rate: Decimal
    employer_eps_rate: Decimal
    employer_edli_rate: Decimal
    admin_charges_rate: Decimal
    statutory_wage_ceiling: Decimal
    eps_wage_ceiling: Decimal
    vpf_allowed: bool
    source_citation: str
    source_document_hash: str
    rule_set_hash: str

    def to_dict(self) -> dict:
        return {
            "rule_version_code": self.rule_version_code,
            "employee_epf_rate": f"{self.employee_epf_rate:.4f}",
            "employer_epf_rate": f"{self.employer_epf_rate:.4f}",
            "employer_eps_rate": f"{self.employer_eps_rate:.4f}",
            "employer_edli_rate": f"{self.employer_edli_rate:.4f}",
            "statutory_wage_ceiling": f"{self.statutory_wage_ceiling:.2f}",
            "eps_wage_ceiling": f"{self.eps_wage_ceiling:.2f}",
            "source_citation": self.source_citation,
            "rule_set_hash": self.rule_set_hash,
        }


@dataclass(frozen=True)
class PfCalculationResult:
    monthly_employee_epf: Decimal
    annual_employee_epf: Decimal
    monthly_employer_epf: Decimal
    annual_employer_epf: Decimal
    monthly_employer_eps: Decimal
    annual_employer_eps: Decimal
    monthly_employer_edli: Decimal
    annual_employer_edli: Decimal
    total_monthly_employer_contribution: Decimal
    total_annual_employer_contribution: Decimal
    rule_version_code: str
