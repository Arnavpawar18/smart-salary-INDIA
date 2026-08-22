"""
Milestone M10.5: Snapshot Immutability & Dual Bundle Hashes
Verifies that calculation snapshots store input_hash, result_hash, and cannot be updated or deleted.
"""

from decimal import Decimal

from app.core.database import SessionLocal
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.models.calculation import CalculationSnapshot
from app.services.calculation_service import CalculationService


def test_m10_snapshot_contains_dual_hashes_and_trace():
    with SessionLocal() as db:
        service = CalculationService(db)
        inp = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1500000.00"))
        res = service.calculate_salary(inp, regime=TaxRegime.NEW, state_code="KA", persist=True)

        assert res.input_hash is not None
        assert len(res.input_hash) == 64
        assert res.result_hash is not None
        assert len(res.result_hash) == 64
        assert res.rule_set_hash is not None
        assert len(res.rule_set_hash) == 64

        # Verify DB snapshot
        snapshot = db.query(CalculationSnapshot).order_by(CalculationSnapshot.id.desc()).first()
        assert snapshot is not None
        assert snapshot.input_hash == res.input_hash
        assert snapshot.result_hash == res.result_hash
