from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.calculation import CalculationRun, CalculationSnapshot, CalculationTrace
from app.presentation.quality import CalculationQuality


class CalculationSaveService:
    """
    Manages calculation persistence lifecycle for authenticated users.
    Implements CURRENT / SUPERSEDED / ARCHIVED immutability pattern.
    Enforces object-level authorization scoped to employee_id.
    """

    def __init__(self, db: Session):
        self.db = db

    def save_calculation_for_employee(
        self,
        employee_id: int,
        financial_year: str,
        regime: str,
        annual_gross: Decimal,
        taxable_income: Decimal,
        total_tax: Decimal,
        take_home: Decimal,
        result_snapshot: dict,
        trace_events: list,
        quality_state: str = CalculationQuality.ESTIMATE.value,
        notes: str | None = None,
    ) -> CalculationRun:
        # 1. Supersede any existing CURRENT calculation for this employee and financial year
        stmt = (
            update(CalculationRun)
            .where(
                CalculationRun.employee_id == employee_id,
                CalculationRun.financial_year == financial_year,
                CalculationRun.status == "CURRENT",
            )
            .values(status="SUPERSEDED")
        )
        self.db.execute(stmt)

        # 2. Create new CURRENT calculation run
        monthly_take_home = (take_home / Decimal("12")).quantize(Decimal("0.01"))
        run = CalculationRun(
            employee_id=employee_id,
            financial_year=financial_year,
            regime=regime,
            total_taxable_income=taxable_income,
            total_tax_liability=total_tax,
            net_take_home_annual=take_home,
            net_take_home_monthly=monthly_take_home,
            status="CURRENT",
        )
        self.db.add(run)
        self.db.flush()

        # 3. Create immutable calculation snapshot
        import hashlib
        import json

        snap_str = json.dumps(result_snapshot, sort_keys=True)
        h = hashlib.sha256(snap_str.encode("utf-8")).hexdigest()
        snapshot = CalculationSnapshot(
            calculation_run_id=run.id,
            input_snapshot={"annual_gross": str(annual_gross), "financial_year": financial_year, "regime": regime},
            result_snapshot=result_snapshot,
            input_hash=h,
            result_hash=h,
            engine_version="1.0.0",
            rounding_policy_version="1.0.0",
        )
        self.db.add(snapshot)

        # 4. Create calculation trace if events present
        if trace_events:
            trace = CalculationTrace(
                calculation_run_id=run.id,
                trace_events_json=trace_events,
                created_at=datetime.now(UTC),
            )
            self.db.add(trace)

        self.db.commit()
        self.db.refresh(run)
        return run

    def get_employee_calculations(
        self,
        employee_id: int,
        status: str | None = None,
    ) -> list[CalculationRun]:
        """Returns calculations belonging strictly to the employee."""
        stmt = select(CalculationRun).where(CalculationRun.employee_id == employee_id)
        if status:
            stmt = stmt.where(CalculationRun.status == status)
        stmt = stmt.order_by(CalculationRun.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def get_employee_calculation_by_id(
        self,
        employee_id: int,
        calculation_id: int,
    ) -> CalculationRun | None:
        """Strict Object-Level IDOR Defense: retrieves calculation only if it belongs to employee."""
        stmt = select(CalculationRun).where(
            CalculationRun.id == calculation_id,
            CalculationRun.employee_id == employee_id,
        )
        return self.db.scalar(stmt)
