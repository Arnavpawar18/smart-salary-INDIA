from dataclasses import dataclass, field
from decimal import Decimal

from app.engine.payslip.discrepancy_codes import DiscrepancyCode
from app.engine.payslip.payslip_extractor import ExtractedPayslipDTO
from app.engine.payslip.tolerance_policy import ReconciliationTolerancePolicy


@dataclass
class ExpectedPayrollDTO:
    """Represents PAYROLL_TRUTH from Phase 5 PayrollRunItem."""

    employee_id: int
    period_code: str
    gross_earnings: Decimal = Decimal("0.00")
    basic: Decimal = Decimal("0.00")
    hra: Decimal = Decimal("0.00")
    special_allowance: Decimal = Decimal("0.00")
    employee_epf: Decimal = Decimal("0.00")
    professional_tax: Decimal = Decimal("0.00")
    tds: Decimal = Decimal("0.00")
    total_deductions: Decimal = Decimal("0.00")
    net_pay: Decimal = Decimal("0.00")
    employer_epf: Decimal = Decimal("0.00")
    payroll_run_id: int | None = None
    payroll_item_id: int | None = None


@dataclass
class StatutoryExpectationDTO:
    """Represents STATUTORY_TRUTH from Phase 2 CalculationSnapshot."""

    annual_gross: Decimal = Decimal("0.00")
    monthly_gross: Decimal = Decimal("0.00")
    monthly_epf: Decimal = Decimal("0.00")
    monthly_pt: Decimal = Decimal("0.00")
    monthly_tds_projected: Decimal = Decimal("0.00")
    snapshot_id: int | None = None
    tax_regime: str = "NEW"


@dataclass
class FieldReconciliationItem:
    field_name: str
    display_name: str
    document_value: Decimal | None
    payroll_value: Decimal | None
    statutory_value: Decimal | None
    delta_document_vs_payroll: Decimal
    delta_document_vs_statutory: Decimal | None
    status: str  # "MATCHED" | "WARNING" | "CRITICAL" | "SKIPPED"
    discrepancy_code: str | None = None
    notes: str | None = None


@dataclass
class ReconciliationResultDTO:
    reconciliation_status: str  # "MATCHED" | "DISCREPANCY_WARNING" | "DISCREPANCY_CRITICAL" | "UNRECONCILED"
    overall_score: float  # 0.0 to 1.0 (1.0 = 100% match)
    total_discrepancies: int
    critical_discrepancies: int
    warning_discrepancies: int
    has_payroll_reference: bool
    has_statutory_reference: bool
    formula_verified: bool
    items: list[FieldReconciliationItem] = field(default_factory=list)
    discrepancy_codes: list[str] = field(default_factory=list)
    summary_explanation: str = ""


class ReconciliationEngine:
    """
    Multi-Status Three-Way Reconciliation Engine.
    Compares:
      Entity A: DOCUMENT_TRUTH (ExtractedPayslipDTO)
      Entity B: PAYROLL_TRUTH (ExpectedPayrollDTO from Phase 5)
      Entity C: STATUTORY_TRUTH (StatutoryExpectationDTO from Phase 2)
    """

    @classmethod
    def reconcile(
        cls,
        document_slip: ExtractedPayslipDTO,
        expected_payroll: ExpectedPayrollDTO | None = None,
        statutory_engine: StatutoryExpectationDTO | None = None,
    ) -> ReconciliationResultDTO:
        items: list[FieldReconciliationItem] = []
        codes: list[str] = []

        has_payroll = expected_payroll is not None
        has_statutory = statutory_engine is not None

        if not has_payroll:
            codes.append(DiscrepancyCode.PAYROLL_REFERENCE_MISSING.value)
        if not has_statutory:
            codes.append(DiscrepancyCode.STATUTORY_REFERENCE_MISSING.value)

        # 1. Check Document Formula Validity first
        if not document_slip.formula_verified:
            codes.append(DiscrepancyCode.DOCUMENT_FORMULA_MISMATCH.value)

        # Fields to compare across 3 dimensions
        comparisons = [
            (
                "gross_earnings",
                "Gross Earnings",
                document_slip.gross_earnings,
                expected_payroll.gross_earnings if has_payroll else None,
                statutory_engine.monthly_gross if has_statutory else None,
                DiscrepancyCode.GROSS_MISMATCH.value,
            ),
            (
                "basic",
                "Basic Salary",
                document_slip.basic,
                expected_payroll.basic if has_payroll else None,
                None,
                DiscrepancyCode.BASIC_MISMATCH.value,
            ),
            (
                "hra",
                "House Rent Allowance (HRA)",
                document_slip.hra,
                expected_payroll.hra if has_payroll else None,
                None,
                DiscrepancyCode.HRA_MISMATCH.value,
            ),
            (
                "employee_epf",
                "Employee EPF",
                document_slip.employee_epf,
                expected_payroll.employee_epf if has_payroll else None,
                statutory_engine.monthly_epf if has_statutory else None,
                DiscrepancyCode.EPF_MISMATCH.value,
            ),
            (
                "professional_tax",
                "Professional Tax (PT)",
                document_slip.professional_tax,
                expected_payroll.professional_tax if has_payroll else None,
                statutory_engine.monthly_pt if has_statutory else None,
                DiscrepancyCode.PT_MISMATCH.value,
            ),
            (
                "tds",
                "Tax Deducted at Source (TDS)",
                document_slip.tds,
                expected_payroll.tds if has_payroll else None,
                statutory_engine.monthly_tds_projected if has_statutory else None,
                DiscrepancyCode.TDS_MISMATCH.value,
            ),
            (
                "total_deductions",
                "Total Deductions",
                document_slip.total_deductions,
                expected_payroll.total_deductions if has_payroll else None,
                None,
                DiscrepancyCode.TOTAL_DEDUCTIONS_MISMATCH.value,
            ),
            (
                "net_pay",
                "Net Take-Home Pay",
                document_slip.net_pay,
                expected_payroll.net_pay if has_payroll else None,
                None,
                DiscrepancyCode.NET_PAY_MISMATCH.value,
            ),
        ]

        critical_count = 0
        warning_count = 0

        for field_name, display_name, doc_val, pay_val, stat_val, mismatch_code in comparisons:
            delta_pay = Decimal("0.00")
            delta_stat: Decimal | None = None
            field_status = "MATCHED"
            assigned_code = None
            notes = []

            # A vs B (Document vs Payroll)
            if pay_val is not None:
                eval_status, delta_pay = ReconciliationTolerancePolicy.evaluate_difference(field_name, doc_val, pay_val)
                if eval_status == "CRITICAL_MISMATCH":
                    field_status = "CRITICAL"
                    assigned_code = mismatch_code
                    critical_count += 1
                    notes.append(f"Differs from employer payroll record by ₹{delta_pay}.")

                    # Specialize EPF under-deduction
                    if field_name == "employee_epf":
                        if doc_val < pay_val:
                            assigned_code = DiscrepancyCode.PF_UNDER_DEDUCTION.value
                        else:
                            assigned_code = DiscrepancyCode.PF_OVER_DEDUCTION.value
                elif eval_status == "TOLERABLE_ROUNDING":
                    field_status = "WARNING"
                    assigned_code = DiscrepancyCode.ROUNDING_VARIANCE.value
                    warning_count += 1
                    notes.append(f"Minor rounding variance of ₹{delta_pay} against payroll.")

            # A vs C (Document vs Statutory)
            if stat_val is not None:
                stat_eval_status, delta_stat = ReconciliationTolerancePolicy.evaluate_difference(
                    field_name, doc_val, stat_val
                )
                if stat_eval_status == "CRITICAL_MISMATCH":
                    if field_status != "CRITICAL":
                        field_status = "CRITICAL"
                        critical_count += 1
                    if not assigned_code:
                        assigned_code = mismatch_code
                    notes.append(f"Differs from statutory engine projection by ₹{delta_stat}.")
                elif stat_eval_status == "TOLERABLE_ROUNDING" and field_status == "MATCHED":
                    field_status = "WARNING"
                    if not assigned_code:
                        assigned_code = DiscrepancyCode.ROUNDING_VARIANCE.value
                    warning_count += 1
                    notes.append(f"Minor rounding variance of ₹{delta_stat} against statutory projection.")

            if assigned_code and assigned_code not in codes:
                codes.append(assigned_code)

            items.append(
                FieldReconciliationItem(
                    field_name=field_name,
                    display_name=display_name,
                    document_value=doc_val,
                    payroll_value=pay_val,
                    statutory_value=stat_val,
                    delta_document_vs_payroll=delta_pay,
                    delta_document_vs_statutory=delta_stat,
                    status=field_status,
                    discrepancy_code=assigned_code,
                    notes="; ".join(notes) if notes else "Matches expected records.",
                )
            )

        # Determine overall reconciliation status
        if critical_count > 0 or not document_slip.formula_verified:
            overall_status = "DISCREPANCY_CRITICAL"
            summary = f"Detected {critical_count} critical financial discrepancy(ies) across actual payslip and statutory/payroll baselines."
        elif warning_count > 0:
            overall_status = "DISCREPANCY_WARNING"
            summary = f"Payslip generally aligns with payroll with {warning_count} minor rounding variance(s)."
        elif not has_payroll and not has_statutory:
            overall_status = "UNRECONCILED"
            summary = "Document parsed successfully, but no matching payroll period or statutory snapshot was found to compare against."
        else:
            overall_status = "MATCHED"
            summary = "100% Concordance: Payslip perfectly matches both employer payroll records and statutory engine calculations."

        total_checks = len(items)
        matched_checks = sum(1 for it in items if it.status == "MATCHED")
        score = round(matched_checks / max(total_checks, 1), 2)

        return ReconciliationResultDTO(
            reconciliation_status=overall_status,
            overall_score=score,
            total_discrepancies=critical_count + warning_count,
            critical_discrepancies=critical_count,
            warning_discrepancies=warning_count,
            has_payroll_reference=has_payroll,
            has_statutory_reference=has_statutory,
            formula_verified=document_slip.formula_verified,
            items=items,
            discrepancy_codes=codes,
            summary_explanation=summary,
        )
