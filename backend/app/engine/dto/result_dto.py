from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional
from app.engine.common.enums import CalculationStatus, LineItemCategory, LineItemType, TaxRegime


@dataclass(frozen=True)
class CalculationAssumptions:
    """Explicit statutory assumptions explaining the scope of the calculation result."""
    salary_income_only: bool = True
    residential_status: str = "RESIDENT"
    age: int = 25
    state: str = "KA"
    pf_applicable: bool = True
    pf_opt_in_higher_wage: bool = False
    tds_provided: bool = False
    other_income_provided: bool = False
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "salary_income_only": self.salary_income_only,
            "residential_status": self.residential_status,
            "age": self.age,
            "state": self.state,
            "pf_applicable": self.pf_applicable,
            "pf_opt_in_higher_wage": self.pf_opt_in_higher_wage,
            "tds_provided": self.tds_provided,
            "other_income_provided": self.other_income_provided,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class CalculationLineItemDTO:
    sequence: int
    category: LineItemCategory
    item_type: LineItemType
    description: str
    base_amount: Decimal
    rate: Decimal
    amount: Decimal
    unit: str = "INR"
    rule_reference: Optional[str] = None
    source_reference: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "sequence": self.sequence,
            "category": self.category.value,
            "item_type": self.item_type.value,
            "description": self.description,
            "base_amount": f"{self.base_amount:.2f}",
            "rate": f"{self.rate:.4f}",
            "amount": f"{self.amount:.2f}",
            "unit": self.unit,
            "rule_reference": self.rule_reference,
            "source_reference": self.source_reference,
        }


@dataclass(frozen=True)
class CalculationTraceStepDTO:
    step_number: int
    title: str
    description: str
    inputs: Dict[str, str]
    outputs: Dict[str, str]
    formula: Optional[str] = None
    legal_reference: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "step_number": self.step_number,
            "title": self.title,
            "description": self.description,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "formula": self.formula,
            "legal_reference": self.legal_reference,
        }


@dataclass(frozen=True)
class VerifiedCalculationResult:
    """Canonical calculation output with complete financial breakdown, ledger, and trace."""
    engine_version: str
    rounding_policy_version: str
    status: CalculationStatus
    financial_year: str
    regime: TaxRegime
    state_code: str
    
    # Financial Summaries
    annual_gross_salary: Decimal
    standard_deduction: Decimal
    taxable_income: Decimal
    
    # Tax Liability Breakdown
    slab_tax: Decimal
    section_87a_rebate: Decimal
    rebate_marginal_relief: Decimal
    tax_after_rebate: Decimal
    surcharge: Decimal
    surcharge_marginal_relief: Decimal
    health_education_cess: Decimal
    total_annual_tax_liability: Decimal
    estimated_monthly_tax: Decimal
    
    # PF & PT Breakdown
    annual_employee_pf: Decimal
    monthly_employee_pf: Decimal
    annual_employer_contribution: Decimal
    monthly_employer_contribution: Decimal
    annual_professional_tax: Decimal
    monthly_professional_tax: Decimal
    
    # Other Employee Deductions
    other_employee_deductions: Decimal
    
    # Net Take-home
    estimated_annual_take_home: Decimal
    estimated_monthly_take_home: Decimal
    
    # Assumptions, Ledger, Traces, Provenance Hashes
    assumptions: CalculationAssumptions
    line_items: List[CalculationLineItemDTO]
    trace_steps: List[CalculationTraceStepDTO]
    
    tax_rule_version_code: str
    pf_rule_version_code: str
    pt_rule_version_code: str
    
    input_hash: str
    result_hash: str
    rule_set_hash: str

    def to_dict(self) -> dict:
        return {
            "engine_version": self.engine_version,
            "rounding_policy_version": self.rounding_policy_version,
            "status": self.status.value,
            "financial_year": self.financial_year,
            "regime": self.regime.value,
            "state_code": self.state_code,
            "annual_gross_salary": f"{self.annual_gross_salary:.2f}",
            "standard_deduction": f"{self.standard_deduction:.2f}",
            "taxable_income": f"{self.taxable_income:.2f}",
            "slab_tax": f"{self.slab_tax:.2f}",
            "section_87a_rebate": f"{self.section_87a_rebate:.2f}",
            "rebate_marginal_relief": f"{self.rebate_marginal_relief:.2f}",
            "tax_after_rebate": f"{self.tax_after_rebate:.2f}",
            "surcharge": f"{self.surcharge:.2f}",
            "surcharge_marginal_relief": f"{self.surcharge_marginal_relief:.2f}",
            "health_education_cess": f"{self.health_education_cess:.2f}",
            "total_annual_tax_liability": f"{self.total_annual_tax_liability:.2f}",
            "estimated_monthly_tax": f"{self.estimated_monthly_tax:.2f}",
            "annual_employee_pf": f"{self.annual_employee_pf:.2f}",
            "monthly_employee_pf": f"{self.monthly_employee_pf:.2f}",
            "annual_employer_contribution": f"{self.annual_employer_contribution:.2f}",
            "monthly_employer_contribution": f"{self.monthly_employer_contribution:.2f}",
            "annual_professional_tax": f"{self.annual_professional_tax:.2f}",
            "monthly_professional_tax": f"{self.monthly_professional_tax:.2f}",
            "other_employee_deductions": f"{self.other_employee_deductions:.2f}",
            "estimated_annual_take_home": f"{self.estimated_annual_take_home:.2f}",
            "estimated_monthly_take_home": f"{self.estimated_monthly_take_home:.2f}",
            "assumptions": self.assumptions.to_dict(),
            "line_items": [li.to_dict() for li in self.line_items],
            "trace_steps": [ts.to_dict() for ts in self.trace_steps],
            "tax_rule_version_code": self.tax_rule_version_code,
            "pf_rule_version_code": self.pf_rule_version_code,
            "pt_rule_version_code": self.pt_rule_version_code,
            "input_hash": self.input_hash,
            "result_hash": self.result_hash,
            "rule_set_hash": self.rule_set_hash,
        }


@dataclass(frozen=True)
class RegimeComparisonResult:
    financial_year: str
    old_regime: VerifiedCalculationResult
    new_regime: VerifiedCalculationResult
    tax_difference: Decimal
    recommended_regime: TaxRegime
    recommendation_note: str

    def to_dict(self) -> dict:
        return {
            "financial_year": self.financial_year,
            "old_regime": self.old_regime.to_dict(),
            "new_regime": self.new_regime.to_dict(),
            "tax_difference": f"{self.tax_difference:.2f}",
            "recommended_regime": self.recommended_regime.value,
            "recommendation_note": self.recommendation_note,
        }
