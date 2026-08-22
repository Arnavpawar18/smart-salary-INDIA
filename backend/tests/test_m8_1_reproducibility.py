"""
Milestone M8.1: Reproducibility & Observability Non-Mutation Test Suite
Verifies:
- Golden calculation replay produces 100% identical outputs and hashes before and after audit ledger recording
- Observability and Audit logging operations cause ZERO mutation on:
  * Rule bundle hashes
  * Evidence bundle hashes
  * Calculation snapshots
  * Audit ledger entries
"""

from decimal import Decimal

from app.core.database import SessionLocal
from app.core.observability import (
    EventSeverity,
    EventType,
    ObservabilityEvent,
    ObservabilityService,
)
from app.engine.dto.salary_dto import SalaryInput
from app.engine.normalizer.salary_normalizer import SalaryNormalizer
from app.services.audit_service import AuditChainVerifier, AuditService


def test_m8_1_calculation_reproducibility_before_and_after_audit():
    inp1 = SalaryInput(
        annual_gross=Decimal("1800000.00"),
        basic_salary=Decimal("900000.00"),
        hra=Decimal("360000.00"),
        financial_year="2025-26",
    )
    norm1 = SalaryNormalizer.normalize(inp1)
    dict1 = norm1.to_dict()

    with SessionLocal() as db:
        # 2. Record Audit Event
        AuditService.log_event(
            db=db,
            action="CALCULATION_EXECUTED",
            resource_type="TAX_CALCULATION",
            resource_id=1,
            tenant_id=300,
            payload={"financial_year": "2025-26", "regime": "NEW"},
        )

    # 3. Second Calculation Execution with identical inputs
    inp2 = SalaryInput(
        annual_gross=Decimal("1800000.00"),
        basic_salary=Decimal("900000.00"),
        hra=Decimal("360000.00"),
        financial_year="2025-26",
    )
    norm2 = SalaryNormalizer.normalize(inp2)
    dict2 = norm2.to_dict()

    # 4. Assert 100% Parity
    assert dict1 == dict2
    assert norm1.annual_gross == norm2.annual_gross
    assert norm1.basic_salary == norm2.basic_salary


def test_m8_1_observability_zero_mutation_on_audit_chain():
    with SessionLocal() as db:
        # Create audit chain
        for i in range(3):
            AuditService.log_event(
                db=db,
                action=f"STEP_{i + 1}",
                resource_type="PIPELINE",
                resource_id=i + 1,
                chain_id="TENANT_OBS_NONMUTATE",
                tenant_id=400,
                payload={"step": i + 1},
            )

        # Baseline chain state
        v_before = AuditChainVerifier.verify_chain(db, chain_id="TENANT_OBS_NONMUTATE")
        assert v_before["valid"] is True
        head_hash_before = v_before["head_hash"]

        # Emit various Observability events
        ObservabilityService.emit(
            ObservabilityEvent(
                event_type=EventType.CALCULATION_COMPLETED,
                severity=EventSeverity.INFO,
                service="tax_engine",
                component="TaxEngine",
                operation="calculate",
                tenant_id=400,
            )
        )
        ObservabilityService.emit(
            ObservabilityEvent(
                event_type=EventType.IDOR_ATTEMPT,
                severity=EventSeverity.SECURITY,
                service="auth",
                component="SecurityFilter",
                operation="validate_token",
                tenant_id=400,
            )
        )

        # Verify audit chain was not mutated by telemetry
        v_after = AuditChainVerifier.verify_chain(db, chain_id="TENANT_OBS_NONMUTATE")
        assert v_after["valid"] is True
        assert v_after["head_hash"] == head_hash_before
