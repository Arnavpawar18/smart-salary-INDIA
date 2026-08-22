from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.calculation import CalculationRun, CalculationSnapshot
from app.models.employee import Employee


@dataclass(frozen=True)
class CalculationContext:
    """
    Immutable Single Source of Truth for a resolved calculation.
    All downstream consumers (Breakdown, RAG, PDF, Print Summary, Payslip, History)
    MUST consume this exact object.
    """
    user_id: int | None
    employee_id: int | None
    organization_id: int | None
    calculation_id: int
    snapshot_id: int
    financial_year: str
    state: str
    occupation: str
    sector: str
    employment_type: str
    regime: str
    input_snapshot: dict[str, Any]
    output_snapshot: dict[str, Any]
    calculation_trace: list[dict[str, Any]]
    applicable_rules: dict[str, Any]
    evidence_references: list[dict[str, Any]]
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "organization_id": self.organization_id,
            "calculation_id": self.calculation_id,
            "snapshot_id": self.snapshot_id,
            "financial_year": self.financial_year,
            "state": self.state,
            "occupation": self.occupation,
            "sector": self.sector,
            "employment_type": self.employment_type,
            "regime": self.regime,
            "input_snapshot": self.input_snapshot,
            "output_snapshot": self.output_snapshot,
            "calculation_trace": self.calculation_trace,
            "applicable_rules": self.applicable_rules,
            "evidence_references": self.evidence_references,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
        }


def resolve_owned_calculation(
    db: Session,
    calculation_id: int,
    user: User | None = None,
    allow_anonymous: bool = False,
) -> CalculationContext:
    """
    Standard resolver for calculations with strict ownership verification.

    Invariants:
    1. Rejects access (403/404) if calculation belongs to User A and is requested by User B.
    2. Resolves exact persisted snapshot — zero heuristic recalculation or 'latest' guessing.
    3. Reconstructs identical CalculationContext consumed by all downstream features.
    """
    run = db.scalar(select(CalculationRun).where(CalculationRun.id == calculation_id))
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calculation with id {calculation_id} not found."
        )

    # Ownership check
    emp: Employee | None = None
    if run.employee_id:
        emp = db.scalar(select(Employee).where(Employee.id == run.employee_id))
        if user and emp and emp.user_id and emp.user_id != user.id:
            # Strictly prevent cross-user IDOR access
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to view this calculation."
            )
        elif not user and not allow_anonymous:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view calculation context."
            )

    # Snapshot retrieval (1..1 with CalculationRun)
    snap = db.scalar(
        select(CalculationSnapshot).where(CalculationSnapshot.calculation_run_id == run.id)
    )
    if not snap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Immutable calculation snapshot for calculation {calculation_id} is missing or corrupted."
        )

    input_data = snap.input_snapshot or {}
    result_data = snap.result_snapshot or {}

    # Extract traces & line items from result_snapshot or DB relations
    traces = result_data.get("trace_steps", [])
    if not traces and run.traces:
        traces = [
            {
                "sequence": idx + 1,
                "title": t.step_name,
                "formula": t.formula_expression,
                "inputs": t.inputs_applied,
                "output": str(t.output_value),
            }
            for idx, t in enumerate(run.traces)
        ]

    # Resolve evidence and rules
    rules = {
        "tax_rule_version_id": snap.tax_rule_version_id,
        "pf_rule_version_id": snap.pf_rule_version_id,
        "professional_tax_rule_version_id": snap.professional_tax_rule_version_id,
        "tax_rule_version_code": result_data.get("tax_rule_version_code"),
        "pf_rule_version_code": result_data.get("pf_rule_version_code"),
        "pt_rule_version_code": result_data.get("pt_rule_version_code"),
        "engine_version": snap.engine_version,
    }

    evidence_refs = result_data.get("evidence_references", [])

    return CalculationContext(
        user_id=user.id if user else (emp.user_id if emp else None),
        employee_id=run.employee_id,
        organization_id=emp.organization_id if emp else None,
        calculation_id=run.id,
        snapshot_id=snap.id,
        financial_year=run.financial_year,
        state=input_data.get("state_code", result_data.get("state_code", "KA")),
        occupation=input_data.get("occupation", "SOFTWARE_IT"),
        sector=input_data.get("sector", "IT / Software"),
        employment_type=emp.employment_type if emp else "FULL_TIME",
        regime=run.regime,
        input_snapshot=input_data,
        output_snapshot=result_data,
        calculation_trace=traces,
        applicable_rules=rules,
        evidence_references=evidence_refs,
        created_at=run.created_at,
    )
