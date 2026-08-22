from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Response, status

from app.core.compliance.evidence_registry import EvidenceRegistry
from app.core.compliance.rule_registry import ComplianceRuleRegistry
from app.core.database import check_db_connection
from app.core.observability import EventSeverity, EventType, ObservabilityEvent, ObservabilityService
from app.core.redis_client import RedisClient
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """
    Dynamic service liveness & PostgreSQL readiness check.
    """
    is_connected = check_db_connection()
    db_status = "connected" if is_connected else "unreachable"
    overall_status = "healthy" if is_connected else "degraded"

    return HealthResponse(
        status=overall_status,
        database=db_status,
        timestamp=datetime.now(UTC),
    )


@router.get("/liveness")
def get_liveness() -> dict[str, Any]:
    """
    Process Liveness Probe: Fast, zero-dependency check of process health.
    Never exposes internal system architecture, passwords, or connection strings.
    """
    return {
        "status": "UP",
        "timestamp": datetime.now(UTC).isoformat(),
        "service": "smartsalary-backend",
    }


@router.get("/readiness")
def get_readiness(response: Response) -> dict[str, Any]:
    """
    Subsystem Readiness Probe: Validates database, rule registry, and evidence registry dependencies.
    Fails with HTTP 503 if critical dependencies are down, emitting structured telemetry.
    """
    db_ready = check_db_connection()
    # Check compliance registries
    rule_count = len(ComplianceRuleRegistry._REGISTRY)
    evidence_count = len(EvidenceRegistry._DOCUMENTS)
    registries_ready = rule_count > 0 and evidence_count > 0

    is_ready = db_ready and registries_ready

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        ObservabilityService.emit(
            ObservabilityEvent(
                event_type=EventType.HEALTH_FAILURE,
                severity=EventSeverity.CRITICAL,
                service="system",
                component="HealthController",
                operation="readiness_check",
                safe_error_code="ERR_SUBSYSTEM_UNREADY",
                details={
                    "database_ready": db_ready,
                    "registries_ready": registries_ready,
                },
            )
        )

    return {
        "status": "READY" if is_ready else "NOT_READY",
        "timestamp": datetime.now(UTC).isoformat(),
        "subsystems": {
            "database": "READY" if db_ready else "UNAVAILABLE",
            "rule_registry": "READY" if registries_ready else "EMPTY",
            "evidence_registry": "READY" if registries_ready else "EMPTY",
        },
    }

@router.get("/redis")
async def get_redis_health() -> dict[str, Any]:
    """Check Redis connectivity and return health status."""
    try:
        client = await RedisClient.get_client()
        pong = await client.ping()
        healthy = pong is True
    except Exception:
        healthy = False
    return {"status": "UP" if healthy else "DOWN", "timestamp": datetime.now(UTC).isoformat()}
