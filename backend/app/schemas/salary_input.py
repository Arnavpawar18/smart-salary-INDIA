from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator


class SalaryComponentsInputSchema(BaseModel):
    basic: Decimal | None = Field(default=None, ge=0)
    da: Decimal | None = Field(default=None, ge=0)
    hra: Decimal | None = Field(default=None, ge=0)
    special_allowance: Decimal | None = Field(default=None, ge=0)
    bonus: Decimal | None = Field(default=None, ge=0)
    other_allowances: Decimal | None = Field(default=None, ge=0)
    other_deductions: Decimal | None = Field(default=None, ge=0)


class ComprehensiveSalaryInputSchema(BaseModel):
    financial_year: str = Field(default="2025-26")
    regime: str = Field(default="NEW")
    state_code: str = Field(default="KA")
    monthly_gross_salary: Decimal | None = Field(default=None, ge=0)
    annual_gross_salary: Decimal | None = Field(default=None, ge=0)
    annual_ctc: Decimal | None = Field(default=None, ge=0)

    # Taxpayer details
    age: int = Field(default=25, ge=18, le=100)
    residential_status: str = Field(default="RESIDENT")

    # Components
    components: SalaryComponentsInputSchema | None = None

    # PF options
    is_pf_applicable: bool = Field(default=True)
    pf_opt_in_higher_wage: bool = Field(default=False)

    # Deductions (OLD regime)
    section_80c: Decimal = Field(default=Decimal("0.00"), ge=0)
    section_80d: Decimal = Field(default=Decimal("0.00"), ge=0)

    # TDS already deducted (for remaining tax calculation)
    tds_already_deducted: Decimal = Field(default=Decimal("0.00"), ge=0)

    @field_validator("regime")
    @classmethod
    def validate_regime(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in ["OLD", "NEW"]:
            raise ValueError(f"Invalid tax regime '{v}'. Must be 'OLD' or 'NEW'.")
        return v_upper

    @model_validator(mode="after")
    def validate_gross_consistency_and_requirements(self) -> "ComprehensiveSalaryInputSchema":
        # 1. Ensure at least one primary income number is provided
        has_primary = (
            self.annual_gross_salary is not None
            or self.monthly_gross_salary is not None
            or self.annual_ctc is not None
            or (self.components and self.components.basic is not None)
        )
        if not has_primary:
            raise ValueError("At least one salary input (monthly_gross, annual_gross, or basic) must be provided.")

        # 2. Strict Gross Consistency Check: |annual - (monthly * 12)| <= 1.00
        if self.annual_gross_salary is not None and self.monthly_gross_salary is not None:
            expected_annual = self.monthly_gross_salary * Decimal("12")
            if abs(self.annual_gross_salary - expected_annual) > Decimal("1.00"):
                raise ValueError(
                    f"Conflicting salary inputs: monthly_gross ₹{self.monthly_gross_salary:,.2f} "
                    f"annualizes to ₹{expected_annual:,.2f}, which conflicts with annual_gross ₹{self.annual_gross_salary:,.2f}."
                )

        return self
