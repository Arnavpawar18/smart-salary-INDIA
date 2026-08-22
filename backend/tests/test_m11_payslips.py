"""
Milestone M11.10: Enterprise Payslip Intelligence
Verifies bulk payslip generation, extraction integrity, and reconciliation against calculation snapshots.
"""

from decimal import Decimal

from app.engine.payslip.payslip_extractor import ExtractedPayslipDTO
from app.engine.payslip.reconciliation_engine import ExpectedPayrollDTO, ReconciliationEngine, StatutoryExpectationDTO


def test_m11_payslip_intelligence_smoke():
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

    stat = StatutoryExpectationDTO(
        monthly_gross=Decimal("80000.00"),
        monthly_epf=Decimal("1800.00"),
        monthly_pt=Decimal("200.00"),
        monthly_tds_projected=Decimal("4500.00"),
    )

    res = ReconciliationEngine.reconcile(doc, payroll, stat)
    assert res.reconciliation_status == "MATCHED"
    assert res.overall_score == 1.0
