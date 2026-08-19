from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.rag.retriever import FinancialRAGRetriever
from app.models.auth import User
from app.models.calculation import CalculationSnapshot
from app.models.payroll import PayrollPeriod, PayrollRunItem
from app.models.payslip import PayslipDocument


@dataclass
class ToolExecutionResult:
    tool_name: str
    is_authorized: bool
    data: dict[str, Any] | None = None
    error_message: str | None = None


class AIToolService:
    """
    Controlled AI Tool Execution Layer.
    Enforces Rule 3: Zero-Direct DB Access for LLMs. Every query is authenticated, authorized, and scoped.
    """

    def __init__(self, db: Session, current_user: User):
        self.db = db
        self.current_user = current_user
        self.retriever = FinancialRAGRetriever(db)

    def get_current_calculation(self) -> ToolExecutionResult:
        if not self.current_user.employee_id:
            return ToolExecutionResult(
                tool_name="get_current_calculation",
                is_authorized=False,
                error_message="User has no linked employee profile.",
            )

        snapshot = self.db.scalar(
            select(CalculationSnapshot)
            .join(CalculationSnapshot.calculation_run)
            .where(
                CalculationSnapshot.calculation_run.property.mapper.class_.employee_id == self.current_user.employee_id,
                CalculationSnapshot.is_active,
            )
            .order_by(CalculationSnapshot.created_at.desc())
        )

        if not snapshot:
            return ToolExecutionResult(
                tool_name="get_current_calculation",
                is_authorized=True,
                data={"status": "NO_CALCULATION_FOUND"},
            )

        return ToolExecutionResult(
            tool_name="get_current_calculation",
            is_authorized=True,
            data={
                "snapshot_id": snapshot.id,
                "financial_year": snapshot.financial_year,
                "tax_regime": snapshot.tax_regime,
                "annual_gross_income": str(snapshot.annual_gross_income),
                "total_tax_liability": str(snapshot.total_tax_liability),
                "total_pf_employee": str(snapshot.total_pf_employee),
                "total_professional_tax": str(snapshot.total_professional_tax),
                "annual_take_home": str(snapshot.annual_take_home),
                "monthly_take_home": str(snapshot.monthly_take_home),
                "effective_tax_rate_pct": str(snapshot.effective_tax_rate_pct),
                "calculation_trace_hash": snapshot.calculation_trace_hash,
            },
        )

    def get_payroll_summary(self, period_code: str) -> ToolExecutionResult:
        if not self.current_user.employee_id:
            return ToolExecutionResult(
                tool_name="get_payroll_summary",
                is_authorized=False,
                error_message="User has no linked employee profile.",
            )

        item = self.db.scalar(
            select(PayrollRunItem)
            .join(PayrollRunItem.payroll_run)
            .join(
                PayrollPeriod, PayrollPeriod.id == PayrollRunItem.payroll_run.property.mapper.class_.payroll_period_id
            )
            .where(
                PayrollRunItem.employee_id == self.current_user.employee_id,
                PayrollPeriod.period_code == period_code,
            )
        )

        if not item:
            return ToolExecutionResult(
                tool_name="get_payroll_summary",
                is_authorized=True,
                data={"status": "NO_PAYROLL_FOUND_FOR_PERIOD", "period_code": period_code},
            )

        return ToolExecutionResult(
            tool_name="get_payroll_summary",
            is_authorized=True,
            data={
                "period_code": period_code,
                "gross_earnings": str(item.gross_earnings),
                "employee_pf": str(item.employee_pf),
                "professional_tax": str(item.professional_tax),
                "tax_tds": str(item.tax_tds),
                "total_deductions": str(item.total_deductions),
                "net_pay": str(item.net_pay),
            },
        )

    def get_payslip_reconciliation(self, document_id: int) -> ToolExecutionResult:
        doc = self.db.scalar(select(PayslipDocument).where(PayslipDocument.id == document_id))
        if not doc:
            return ToolExecutionResult(
                tool_name="get_payslip_reconciliation",
                is_authorized=False,
                error_message="Payslip document not found.",
            )

        # IDOR Boundary Check
        user_roles = [r.name for r in self.current_user.roles]
        is_hr_or_admin = any(r in ["SUPER_ADMIN", "ADMIN", "HR_MANAGER", "PAYROLL_ADMIN"] for r in user_roles)
        if not is_hr_or_admin and doc.employee_id != self.current_user.employee_id:
            return ToolExecutionResult(
                tool_name="get_payslip_reconciliation",
                is_authorized=False,
                error_message="Access Denied: You cannot view another employee's payslip.",
            )

        val = doc.validations[0] if doc.validations else None
        return ToolExecutionResult(
            tool_name="get_payslip_reconciliation",
            is_authorized=True,
            data={
                "document_id": doc.id,
                "file_name": doc.file_name,
                "reconciliation_status": val.validation_status if val else "UNRECONCILED",
                "discrepancy_flags": val.discrepancy_flags if val else {},
            },
        )

    def search_official_knowledge(self, query: str, financial_year: str = "2025-26") -> ToolExecutionResult:
        evidence = self.retriever.retrieve_evidence(query=query, financial_year=financial_year)
        return ToolExecutionResult(
            tool_name="search_official_knowledge",
            is_authorized=True,
            data={
                "query": query,
                "chunks": [
                    {
                        "chunk_id": c.chunk_id,
                        "title": c.title,
                        "authority": c.authority,
                        "section": c.section_reference,
                        "content": c.content,
                    }
                    for c in evidence.chunks
                ],
            },
        )
