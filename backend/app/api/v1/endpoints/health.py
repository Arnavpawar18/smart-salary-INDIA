from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.database import check_db_connection
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
