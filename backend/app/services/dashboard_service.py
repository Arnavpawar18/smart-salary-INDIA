from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.calculation import CalculationRun, CalculationSnapshot
from app.presentation.money import format_inr
from app.services.scenario_service import ScenarioService


class DashboardService:
    """
    Financial summary, FY trend, and 'What Changed?' engine for authenticated employee dashboard.
    Strictly uses stored calculation snapshots and never recalculates historical records.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_employee_dashboard_summary(self, employee_id: int) -> dict[str, Any]:
        """
        Retrieves current calculation summary, multi-year historical trend, and recent runs.
        """
        # 1. Fetch latest CURRENT calculation run
        stmt_current = (
            select(CalculationRun)
            .where(
                CalculationRun.employee_id == employee_id,
                CalculationRun.status == "CURRENT",
            )
            .order_by(CalculationRun.created_at.desc())
        )
        current_run = self.db.scalar(stmt_current)

        # 2. Fetch all historical calculations for the employee (CURRENT + SUPERSEDED)
        stmt_history = (
            select(CalculationRun)
            .where(CalculationRun.employee_id == employee_id)
            .order_by(CalculationRun.created_at.desc())
        )
        all_runs = list(self.db.scalars(stmt_history).all())

        # 3. Build FY Trend (using stored snapshots)
        fy_trend = []
        # Distinct financial years present
        seen_fys = set()
        for run in all_runs:
            if run.financial_year not in seen_fys:
                seen_fys.add(run.financial_year)
                # Parse snapshot
                snapshot = self.db.scalar(
                    select(CalculationSnapshot).where(CalculationSnapshot.calculation_run_id == run.id)
                )
                snap_res = snapshot.result_snapshot if snapshot else {}
                taxable = run.total_taxable_income
                tax = run.total_tax_liability
                take_home = run.net_take_home_annual
                annual_gross = snap_res.get("annual_gross_salary", str(take_home + tax))
                pf = snap_res.get("annual_employee_pf", "0.00")
                pt = snap_res.get("annual_pt", "0.00")

                eff_tax_rate = (
                    (tax / float(annual_gross) * 100)
                    if float(annual_gross) > 0
                    else 0.0
                )

                fy_trend.append({
                    "financial_year": run.financial_year,
                    "regime": run.regime,
                    "annual_gross": annual_gross,
                    "annual_gross_formatted": format_inr(annual_gross),
                    "taxable_income": str(taxable),
                    "taxable_income_formatted": format_inr(taxable),
                    "tax": str(tax),
                    "tax_formatted": format_inr(tax),
                    "employee_pf": pf,
                    "employee_pf_formatted": format_inr(pf),
                    "pt": pt,
                    "pt_formatted": format_inr(pt),
                    "take_home": str(take_home),
                    "take_home_formatted": format_inr(take_home),
                    "effective_tax_rate": round(eff_tax_rate, 2),
                    "calculation_id": run.id,
                })

        # 4. What Changed Year-over-Year (if at least 2 distinct FYs exist)
        what_changed = None
        if len(fy_trend) >= 2:
            current_snap = self.db.scalar(
                select(CalculationSnapshot).where(CalculationSnapshot.calculation_run_id == fy_trend[0]["calculation_id"])
            )
            prev_snap = self.db.scalar(
                select(CalculationSnapshot).where(CalculationSnapshot.calculation_run_id == fy_trend[1]["calculation_id"])
            )
            if current_snap and prev_snap:
                what_changed = ScenarioService.compute_what_changed_delta(
                    baseline_run=prev_snap.result_snapshot,
                    new_run=current_snap.result_snapshot,
                )

        return {
            "current_run": current_run,
            "fy_trend": fy_trend,
            "recent_calculations": all_runs[:10],
            "what_changed": what_changed,
        }
