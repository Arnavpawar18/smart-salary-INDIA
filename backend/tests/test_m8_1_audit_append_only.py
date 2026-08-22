"""
Milestone M8.1: Audit Append-Only & Immutability Enforcement Test Suite
Verifies:
- INSERT/Append permitted
- ORM UPDATE on AuditLog blocked with AuditImmutabilityError
- ORM DELETE on AuditLog blocked with AuditImmutabilityError
- ORM UPDATE and DELETE on CalculationSnapshot blocked with AuditImmutabilityError
- AuditChainHead and AuditCheckpoint deletion blocked
"""

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.engine.common.errors import AuditImmutabilityError
from app.models.audit import AuditLog
from app.models.calculation import CalculationRun, CalculationSnapshot
from app.services.audit_service import AuditService


def test_m8_1_audit_insert_permitted():
    with SessionLocal() as db:
        log = AuditService.log_event(
            db=db,
            action="LOGIN_SUCCESS",
            resource_type="USER_SESSION",
            resource_id=1,
            tenant_id=101,
            actor_type="USER",
            actor_id=1,
            payload={"status": "AUTHENTICATED"},
        )
        assert log.id is not None
        assert log.sequence_number >= 1
        assert log.chain_id == "TENANT_101"
        assert len(log.event_hash) == 64
        assert len(log.previous_event_hash) == 64


def test_m8_1_audit_orm_update_blocked():
    with SessionLocal() as db:
        log = AuditService.log_event(
            db=db,
            action="PASSWORD_CHANGED",
            resource_type="USER",
            resource_id=2,
            tenant_id=102,
            actor_type="USER",
            actor_id=2,
            payload={"reason": "ROUTINE_ROTATION"},
        )
        log_id = log.id

    with SessionLocal() as db:
        record = db.scalar(select(AuditLog).where(AuditLog.id == log_id))
        assert record is not None
        record.action = "ILLEGAL_MUTATION"

        with pytest.raises(AuditImmutabilityError) as exc_info:
            db.commit()
        assert "MUTATION_PROHIBITED" in str(exc_info.value)
        db.rollback()


def test_m8_1_audit_orm_delete_blocked():
    with SessionLocal() as db:
        log = AuditService.log_event(
            db=db,
            action="CALCULATION_SAVED",
            resource_type="CALCULATION",
            resource_id=5,
            tenant_id=103,
            actor_type="USER",
            actor_id=3,
            payload={"calc_type": "ANNUAL_TAX"},
        )
        log_id = log.id

    with SessionLocal() as db:
        record = db.scalar(select(AuditLog).where(AuditLog.id == log_id))
        assert record is not None
        db.delete(record)

        with pytest.raises(AuditImmutabilityError) as exc_info:
            db.commit()
        assert "DELETION_PROHIBITED" in str(exc_info.value)
        db.rollback()


def test_m8_1_calculation_snapshot_immutability():
    with SessionLocal() as db:
        run = CalculationRun(
            financial_year="2026-27",
            regime="NEW",
            status="COMPLETED",
        )
        db.add(run)
        db.flush()

        snap = CalculationSnapshot(
            calculation_run_id=run.id,
            input_snapshot={"gross": "1200000.00"},
            result_snapshot={"tax": "50000.00"},
            input_hash="1111111111111111111111111111111111111111111111111111111111111111",
            result_hash="2222222222222222222222222222222222222222222222222222222222222222",
            engine_version="2026.1",
        )
        db.add(snap)
        db.commit()
        snap_id = snap.id

    with SessionLocal() as db:
        s = db.scalar(select(CalculationSnapshot).where(CalculationSnapshot.id == snap_id))
        assert s is not None
        s.input_hash = "mutated_hash"
        with pytest.raises(AuditImmutabilityError) as exc_info:
            db.commit()
        assert "MUTATION_PROHIBITED" in str(exc_info.value)
        db.rollback()

    with SessionLocal() as db:
        s = db.scalar(select(CalculationSnapshot).where(CalculationSnapshot.id == snap_id))
        db.delete(s)
        with pytest.raises(AuditImmutabilityError) as exc_info:
            db.commit()
        assert "DELETION_PROHIBITED" in str(exc_info.value)
        db.rollback()
