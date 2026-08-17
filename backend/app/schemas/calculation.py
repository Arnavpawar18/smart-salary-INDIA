from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SalaryComponentsRequest(BaseModel):
    basic: Optional[Decimal] = Field(default=None, ge=0)
    da: Optional[Decimal] = Field(default=None, ge=0)
    hra: Optional[Decimal] = Field(default=None, ge=0)
    special_allowance: Optional[Decimal] = Field(default=None, ge=0)
    bonus: Optional[Decimal] = Field(default=None, ge=0)
    other_allowances: Optional[Decimal] = Field(default=None, ge=0)
    other_deductions: Optional[Decimal] = Field(default=None, ge=0)


class CalculationRequest(BaseModel):
    financial_year: str = Field(default="2025-26")
    regime: str = Field(default="NEW")
    state_code: str = Field(default="KA")
    annual_gross_salary: Optional[Decimal] = Field(default=None, ge=0)
    monthly_gross_salary: Optional[Decimal] = Field(default=None, ge=0)
    annual_ctc: Optional[Decimal] = Field(default=None, ge=0)
    age: int = Field(default=25, ge=18, le=100)
    components: Optional[SalaryComponentsRequest] = None
    pf_opt_in_higher_wage: bool = Field(default=False)
    section_80c: Decimal = Field(default=Decimal("0.00"), ge=0)
    section_80d: Decimal = Field(default=Decimal("0.00"), ge=0)


class LineItemResponse(BaseModel):
    sequence: int
    category: str
    item_type: str
    description: str
    base_amount: str
    rate: str
    amount: str
    unit: str
    rule_reference: Optional[str] = None


class TraceStepResponse(BaseModel):
    step_number: int
    title: str
    description: str
    inputs: Dict[str, str]
    outputs: Dict[str, str]
    formula: Optional[str] = None
    legal_reference: Optional[str] = None


class CalculationResponse(BaseModel):
    engine_version: str
    rounding_policy_version: str
    status: str
    financial_year: str
    regime: str
    state_code: str

    annual_gross_salary: str
    standard_deduction: str
    taxable_income: str

    slab_tax: str
    section_87a_rebate: str
    rebate_marginal_relief: str
    health_education_cess: str
    total_annual_tax_liability: str
    estimated_monthly_tax: str

    annual_employee_pf: str
    monthly_employee_pf: str
    annual_employer_contribution: str
    annual_professional_tax: str
    monthly_professional_tax: str
    other_employee_deductions: str

    estimated_annual_take_home: str
    estimated_monthly_take_home: str

    assumptions: Dict[str, Any]
    line_items: List[LineItemResponse]
    trace_steps: List[TraceStepResponse]

    tax_rule_version_code: str
    pf_rule_version_code: str
    pt_rule_version_code: str

    input_hash: str
    result_hash: str
    rule_set_hash: str


class RegimeComparisonResponse(BaseModel):
    financial_year: str
    old_regime: CalculationResponse
    new_regime: CalculationResponse
    tax_difference: str
    recommended_regime: str
    recommendation_note: str
