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

    def _get_user_employee_id(self) -> int | None:
        if hasattr(self.current_user, "employee_id") and self.current_user.employee_id:
            return self.current_user.employee_id
        if hasattr(self.current_user, "employee") and self.current_user.employee:
            return self.current_user.employee.id
        # Fallback: query employee from DB by user_id
        if self.db is not None:
            from app.models.employee import Employee
            emp = self.db.scalar(select(Employee).where(Employee.user_id == self.current_user.id))
            return emp.id if emp else None
        return None

    def get_current_calculation(self, snapshot_id: int | None = None) -> ToolExecutionResult:
        from app.models.calculation import CalculationRun

        emp_id = self._get_user_employee_id()
        if not emp_id:
            return ToolExecutionResult(
                tool_name="get_current_calculation",
                is_authorized=False,
                error_message="User has no linked employee profile.",
            )

        query = (
            select(CalculationSnapshot)
            .join(CalculationRun, CalculationSnapshot.calculation_run_id == CalculationRun.id)
            .where(CalculationRun.employee_id == emp_id)
        )

        if snapshot_id is not None:
            # Explicit snapshot requested: check if it belongs to this employee
            target = self.db.scalar(select(CalculationSnapshot).where(CalculationSnapshot.id == snapshot_id))
            if target:
                run = self.db.scalar(select(CalculationRun).where(CalculationRun.id == target.calculation_run_id))
                if not run or run.employee_id != emp_id:
                    return ToolExecutionResult(
                        tool_name="get_current_calculation",
                        is_authorized=False,
                        error_message="Access Denied: You cannot access calculation snapshots belonging to another employee.",
                    )
            query = query.where(CalculationSnapshot.id == snapshot_id)

        snapshot = self.db.scalar(query.order_by(CalculationSnapshot.created_at.desc()))

        if not snapshot:
            return ToolExecutionResult(
                tool_name="get_current_calculation",
                is_authorized=True,
                data={"status": "NO_CALCULATION_FOUND"},
            )

        run = snapshot.calculation_run
        res_snap = snapshot.result_snapshot or {}
        inp_snap = snapshot.input_snapshot or {}

        return ToolExecutionResult(
            tool_name="get_current_calculation",
            is_authorized=True,
            data={
                "snapshot_id": snapshot.id,
                "financial_year": run.financial_year if run else inp_snap.get("financial_year", "2025-26"),
                "tax_regime": run.regime if run else inp_snap.get("regime", "NEW"),
                "annual_gross_income": str(inp_snap.get("annual_gross_salary", inp_snap.get("annual_gross", "0"))),
                "total_tax_liability": str(run.total_tax_liability if run else res_snap.get("total_tax_liability", "0")),
                "annual_take_home": str(run.net_take_home_annual if run else res_snap.get("net_take_home_annual", "0")),
                "monthly_take_home": str(run.net_take_home_monthly if run else res_snap.get("net_take_home_monthly", "0")),
                "result_hash": snapshot.result_hash,
                "input_hash": snapshot.input_hash,
            },
        )

    def get_payroll_summary(self, period_code: str) -> ToolExecutionResult:
        emp_id = self._get_user_employee_id()
        if not emp_id:
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
                PayrollRunItem.employee_id == emp_id,
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
        emp_id = self._get_user_employee_id()
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
        if not is_hr_or_admin and doc.employee_id != emp_id:
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
