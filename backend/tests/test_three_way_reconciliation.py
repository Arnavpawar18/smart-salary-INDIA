from decimal import Decimal

from app.engine.payslip.discrepancy_codes import DiscrepancyCode
from app.engine.payslip.payslip_extractor import ExtractedPayslipDTO
from app.engine.payslip.reconciliation_engine import (
    ExpectedPayrollDTO,
    ReconciliationEngine,
    StatutoryExpectationDTO,
)


def test_reconciliation_exact_three_way_match():
    # A: Document
    doc = ExtractedPayslipDTO(
        gross_earnings=Decimal("80000.00"),
        basic=Decimal("40000.00"),
        hra=Decimal("20000.00"),
        special_allowance=Decimal("20000.00"),
        employee_epf=Decimal("1800.00"),
        professional_tax=Decimal("200.00"),
        tds=Decimal("4500.00"),
        total_deductions=Decimal("6500.00"),
        net_pay=Decimal("73500.00"),
        formula_verified=True,
    )

    # B: Payroll
    payroll = ExpectedPayrollDTO(
        employee_id=1,
        period_code="2026-04",
        gross_earnings=Decimal("80000.00"),
        basic=Decimal("40000.00"),
        hra=Decimal("20000.00"),
        special_allowance=Decimal("20000.00"),
        employee_epf=Decimal("1800.00"),
        professional_tax=Decimal("200.00"),
        tds=Decimal("4500.00"),
        total_deductions=Decimal("6500.00"),
        net_pay=Decimal("73500.00"),
    )

    # C: Statutory Engine
    stat = StatutoryExpectationDTO(
        monthly_gross=Decimal("80000.00"),
        monthly_epf=Decimal("1800.00"),
        monthly_pt=Decimal("200.00"),
        monthly_tds_projected=Decimal("4500.00"),
    )

    res = ReconciliationEngine.reconcile(doc, payroll, stat)
    assert res.reconciliation_status == "MATCHED"
    assert res.overall_score == 1.0
    assert res.critical_discrepancies == 0
    assert res.warning_discrepancies == 0
    assert len(res.discrepancy_codes) == 0


def test_reconciliation_pf_under_deduction_critical():
    # Document has under-deducted EPF (₹1,500 instead of statutory ₹1,800)
    doc = ExtractedPayslipDTO(
        gross_earnings=Decimal("80000.00"),
        basic=Decimal("40000.00"),
        hra=Decimal("20000.00"),
        employee_epf=Decimal("1500.00"),  # Under-deducted
        professional_tax=Decimal("200.00"),
        tds=Decimal("4500.00"),
        total_deductions=Decimal("6200.00"),
        net_pay=Decimal("73800.00"),
        formula_verified=True,
    )

    payroll = ExpectedPayrollDTO(
        employee_id=1,
        period_code="2026-04",
        gross_earnings=Decimal("80000.00"),
        basic=Decimal("40000.00"),
        hra=Decimal("20000.00"),
        employee_epf=Decimal("1800.00"),
        professional_tax=Decimal("200.00"),
        tds=Decimal("4500.00"),
        total_deductions=Decimal("6500.00"),
        net_pay=Decimal("73500.00"),
    )

    stat = StatutoryExpectationDTO(
        monthly_gross=Decimal("80000.00"),
        monthly_epf=Decimal("1800.00"),
        monthly_pt=Decimal("200.00"),
        monthly_tds_projected=Decimal("4500.00"),
    )

    res = ReconciliationEngine.reconcile(doc, payroll, stat)
    assert res.reconciliation_status == "DISCREPANCY_CRITICAL"
    assert DiscrepancyCode.PF_UNDER_DEDUCTION.value in res.discrepancy_codes
    assert res.critical_discrepancies >= 1


def test_reconciliation_tolerable_rounding_warning():
    # TDS has ₹2 rounding variance (within TDS tolerance threshold)
    doc = ExtractedPayslipDTO(
        gross_earnings=Decimal("80000.00"),
        basic=Decimal("40000.00"),
        hra=Decimal("20000.00"),
        employee_epf=Decimal("1800.00"),
        professional_tax=Decimal("200.00"),
        tds=Decimal("4502.00"),  # ₹2 rounding
        total_deductions=Decimal("6502.00"),
        net_pay=Decimal("73498.00"),
        formula_verified=True,
    )

    payroll = ExpectedPayrollDTO(
        employee_id=1,
        period_code="2026-04",
        gross_earnings=Decimal("80000.00"),
        basic=Decimal("40000.00"),
        hra=Decimal("20000.00"),
        employee_epf=Decimal("1800.00"),
        professional_tax=Decimal("200.00"),
        tds=Decimal("4500.00"),
        total_deductions=Decimal("6500.00"),
        net_pay=Decimal("73500.00"),
    )

    res = ReconciliationEngine.reconcile(doc, payroll, None)
    assert res.reconciliation_status == "DISCREPANCY_WARNING"
    assert DiscrepancyCode.ROUNDING_VARIANCE.value in res.discrepancy_codes
    assert res.critical_discrepancies == 0


def test_reconciliation_document_formula_mismatch():
    # Document math is invalid (Gross - Deductions != Net)
    doc = ExtractedPayslipDTO(
        gross_earnings=Decimal("80000.00"),
        total_deductions=Decimal("6500.00"),
        net_pay=Decimal("70000.00"),  # Should be 73,500
        formula_verified=False,
    )

    res = ReconciliationEngine.reconcile(doc, None, None)
    assert res.reconciliation_status == "DISCREPANCY_CRITICAL"
    assert DiscrepancyCode.DOCUMENT_FORMULA_MISMATCH.value in res.discrepancy_codes
