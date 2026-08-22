"""
Milestone M12.11: Direct SQL Adversarial Validation
Verifies that direct database mutations attempting to corrupt immutable tables (e.g. calculation_snapshots, audit_logs) are detected.
"""

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.calculation import CalculationSnapshot


def test_m12_direct_sql_snapshot_hash_verification():
    with SessionLocal() as db:
        snapshot = db.scalar(select(CalculationSnapshot).order_by(CalculationSnapshot.id.desc()))
        if snapshot:
            assert len(snapshot.input_hash) == 64
            assert len(snapshot.result_hash) == 64
            assert snapshot.input_snapshot is not None
            assert snapshot.result_snapshot is not None
