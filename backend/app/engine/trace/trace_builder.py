from decimal import Decimal

from app.engine.common.enums import LineItemCategory, LineItemType
from app.engine.dto.pf_dto import PfCalculationResult, PfRuleSet
from app.engine.dto.pt_dto import PtCalculationResult, PtRuleSet
from app.engine.dto.result_dto import CalculationLineItemDTO, CalculationTraceStepDTO
from app.engine.dto.salary_dto import NormalizedSalary
from app.engine.dto.tax_dto import TaxRuleSet


class TraceBuilder:
    """
    Constructs deterministic, machine-readable line items and human-readable explanation trace steps
    for every calculation run with statutory rule citations.
    """

    @classmethod
    def build_ledger_and_trace(
        cls,
        salary: NormalizedSalary,
        tax_res: dict[str, Decimal],
        pf_res: PfCalculationResult,
        pt_res: PtCalculationResult,
        tax_rules: TaxRuleSet,
        pf_rules: PfRuleSet,
        pt_rules: PtRuleSet,
    ) -> tuple[list[CalculationLineItemDTO], list[CalculationTraceStepDTO]]:
        line_items: list[CalculationLineItemDTO] = []
        trace_steps: list[CalculationTraceStepDTO] = []
        seq = 1

        # 1. Income Items
        line_items.append(
            CalculationLineItemDTO(
                sequence=seq,
                category=LineItemCategory.INCOME,
                item_type=LineItemType.BASIC,
                description="Basic Salary component",
                base_amount=salary.basic_salary,
                rate=Decimal("1.0000"),
                amount=salary.basic_salary,
            )
        )
        seq += 1

        if salary.hra > Decimal("0.00"):
            line_items.append(
                CalculationLineItemDTO(
                    sequence=seq,
                    category=LineItemCategory.INCOME,
                    item_type=LineItemType.HRA,
                    description="House Rent Allowance component",
                    base_amount=salary.hra,
                    rate=Decimal("1.0000"),
                    amount=salary.hra,
                )
            )
            seq += 1

        if salary.special_allowance > Decimal("0.00"):
            line_items.append(
                CalculationLineItemDTO(
                    sequence=seq,
                    category=LineItemCategory.INCOME,
                    item_type=LineItemType.SPECIAL_ALLOWANCE,
                    description="Special Allowance component",
                    base_amount=salary.special_allowance,
                    rate=Decimal("1.0000"),
                    amount=salary.special_allowance,
                )
            )
            seq += 1

        line_items.append(
            CalculationLineItemDTO(
                sequence=seq,
                category=LineItemCategory.INCOME,
                item_type=LineItemType.GROSS_SALARY,
                description="Total Annual Gross Salary",
                base_amount=salary.annual_gross,
                rate=Decimal("1.0000"),
                amount=salary.annual_gross,
            )
        )
        seq += 1

        trace_steps.append(
            CalculationTraceStepDTO(
                step_number=1,
                title="Gross Salary Computation",
                description="Aggregated all salary components to determine annual gross salary.",
                inputs={
                    "Basic": f"₹{salary.basic_salary:,.2f}",
                    "HRA": f"₹{salary.hra:,.2f}",
                    "Special": f"₹{salary.special_allowance:,.2f}",
                },
                outputs={"Gross Salary": f"₹{salary.annual_gross:,.2f}"},
                formula="Gross Salary = Basic + HRA + Special Allowance + Other Allowances",
            )
        )

        # 2. Deductions & Taxable Income
        std_ded = tax_res["standard_deduction"]
        if std_ded > Decimal("0.00"):
            line_items.append(
                CalculationLineItemDTO(
                    sequence=seq,
                    category=LineItemCategory.DEDUCTION,
                    item_type=LineItemType.STANDARD_DEDUCTION,
                    description="Statutory Standard Deduction under Section 16(ia)",
                    base_amount=salary.annual_gross,
                    rate=Decimal("1.0000"),
                    amount=std_ded,
                    rule_reference=tax_rules.rule_version_code,
                    source_reference=tax_rules.source_citation,
                )
            )
            seq += 1

        taxable_inc = tax_res["taxable_income"]
        line_items.append(
            CalculationLineItemDTO(
                sequence=seq,
                category=LineItemCategory.TAXABLE_INCOME,
                item_type=LineItemType.GROSS_SALARY,
                description="Net Taxable Income after statutory deductions",
                base_amount=taxable_inc,
                rate=Decimal("1.0000"),
                amount=taxable_inc,
            )
        )
        seq += 1

        trace_steps.append(
            CalculationTraceStepDTO(
                step_number=2,
                title="Statutory Deductions & Taxable Income",
                description="Applied Section 16(ia) standard deduction and eligible Chapter VI-A deductions.",
                inputs={"Gross Salary": f"₹{salary.annual_gross:,.2f}", "Standard Deduction": f"₹{std_ded:,.2f}"},
                outputs={"Taxable Income": f"₹{taxable_inc:,.2f}"},
                formula="Taxable Income = max(0, Gross Salary - Total Deductions)",
                legal_reference="Section 16(ia), Income-tax Act, 1961",
            )
        )

        # 3. Slab Tax & Rebate
        slab_tax = tax_res["slab_tax"]
        line_items.append(
            CalculationLineItemDTO(
                sequence=seq,
                category=LineItemCategory.TAX_SLAB,
                item_type=LineItemType.TOTAL_ANNUAL_TAX,
                description=f"Progressive slab tax computed under {tax_rules.regime.value} regime",
                base_amount=taxable_inc,
                rate=Decimal("0.0000"),
                amount=slab_tax,
                rule_reference=tax_rules.rule_version_code,
            )
        )
        seq += 1

        rebate = tax_res["section_87a_rebate"]
        if rebate > Decimal("0.00"):
            line_items.append(
                CalculationLineItemDTO(
                    sequence=seq,
                    category=LineItemCategory.REBATE,
                    item_type=LineItemType.SECTION_87A_REBATE,
                    description="Statutory Tax Rebate under Section 87A",
                    base_amount=taxable_inc,
                    rate=Decimal("1.0000"),
                    amount=rebate,
                    rule_reference="Section 87A",
                )
            )
            seq += 1

        cess = tax_res["health_education_cess"]
        line_items.append(
            CalculationLineItemDTO(
                sequence=seq,
                category=LineItemCategory.CESS,
                item_type=LineItemType.HEALTH_EDUCATION_CESS,
                description="Health and Education Cess (4%)",
                base_amount=tax_res["tax_after_rebate"] + tax_res["surcharge"] - tax_res["surcharge_marginal_relief"],
                rate=Decimal("0.0400"),
                amount=cess,
            )
        )
        seq += 1

        total_tax = tax_res["total_annual_tax_liability"]
        line_items.append(
            CalculationLineItemDTO(
                sequence=seq,
                category=LineItemCategory.TAX_LIABILITY,
                item_type=LineItemType.TOTAL_ANNUAL_TAX,
                description="Total Estimated Annual Income Tax Liability (rounded u/s 288B)",
                base_amount=total_tax,
                rate=Decimal("1.0000"),
                amount=total_tax,
            )
        )
        seq += 1

        trace_steps.append(
            CalculationTraceStepDTO(
                step_number=3,
                title="Tax Liability & Cess Computation",
                description="Computed bracket tax, applied Section 87A rebate and 4% Health & Education cess.",
                inputs={
                    "Taxable Income": f"₹{taxable_inc:,.2f}",
                    "Slab Tax": f"₹{slab_tax:,.2f}",
                    "Rebate 87A": f"₹{rebate:,.2f}",
                },
                outputs={"Cess (4%)": f"₹{cess:,.2f}", "Total Annual Tax Liability": f"₹{total_tax:,.2f}"},
                formula="Total Tax = round_to_10((Slab Tax - Rebate + Surcharge) * 1.04)",
                legal_reference="Section 115BAC & Section 288B, Income-tax Act, 1961",
            )
        )

        # 4. Provident Fund & Professional Tax
        emp_pf = pf_res.annual_employee_epf
        if emp_pf > Decimal("0.00"):
            line_items.append(
                CalculationLineItemDTO(
                    sequence=seq,
                    category=LineItemCategory.PF_CONTRIBUTION,
                    item_type=LineItemType.EMPLOYEE_EPF,
                    description="Annual Employee EPF Contribution (12% of applicable wage base)",
                    base_amount=salary.pf_wage_base_monthly * Decimal("12"),
                    rate=pf_rules.employee_epf_rate,
                    amount=emp_pf,
                    rule_reference=pf_rules.rule_version_code,
                    source_reference=pf_rules.source_citation,
                )
            )
            seq += 1

        pt_annual = pt_res.annual_pt
        if pt_annual > Decimal("0.00"):
            line_items.append(
                CalculationLineItemDTO(
                    sequence=seq,
                    category=LineItemCategory.PROFESSIONAL_TAX,
                    item_type=LineItemType.ANNUAL_PT,
                    description=f"State Professional Tax for {pt_rules.state_name} ({pt_rules.state_code})",
                    base_amount=salary.monthly_gross,
                    rate=Decimal("1.0000"),
                    amount=pt_annual,
                    rule_reference=pt_rules.rule_version_code,
                    source_reference=pt_rules.source_citation,
                )
            )
            seq += 1

        # 5. Net Estimated Take-home
        take_home_annual = salary.annual_gross - total_tax - emp_pf - pt_annual - salary.other_employee_deductions
        line_items.append(
            CalculationLineItemDTO(
                sequence=seq,
                category=LineItemCategory.TAKE_HOME,
                item_type=LineItemType.ESTIMATED_TAKE_HOME,
                description="Estimated Net Annual Take-home Salary",
                base_amount=salary.annual_gross,
                rate=Decimal("1.0000"),
                amount=take_home_annual,
            )
        )

        trace_steps.append(
            CalculationTraceStepDTO(
                step_number=4,
                title="Estimated Take-Home Reconciliation",
                description="Reconciled gross earnings with all statutory employee deductions.",
                inputs={
                    "Annual Gross": f"₹{salary.annual_gross:,.2f}",
                    "Income Tax": f"₹{total_tax:,.2f}",
                    "Employee PF": f"₹{emp_pf:,.2f}",
                    "Professional Tax": f"₹{pt_annual:,.2f}",
                },
                outputs={
                    "Estimated Annual Take-Home": f"₹{take_home_annual:,.2f}",
                    "Monthly Take-Home": f"₹{take_home_annual / Decimal('12'):,.2f}",
                },
                formula="Take-Home = Gross Salary - Tax Liability - Employee PF - Professional Tax - Other Employee Deductions",
            )
        )

        return line_items, trace_steps
