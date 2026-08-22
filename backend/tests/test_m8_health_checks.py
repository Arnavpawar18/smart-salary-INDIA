"""
M8 Health & Readiness Diagnostic Suite
Verifies:
- HTTP /liveness vs /readiness behavior across positive and degraded scenarios
- Health check endpoints never disclose internal secrets, passwords, connection strings, or stack traces
- Telemetry emission upon readiness degradation
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.observability import EventSeverity, EventType, ObservabilityService
from app.main import app


@pytest.fixture(autouse=True)
def clean_telemetry():
    ObservabilityService.clear_events()
    yield
    ObservabilityService.clear_events()


def test_m8_health_checks_liveness_and_readiness_safety():
    client = TestClient(app)

    # 1. Liveness Probe (always 200 process-level)
    resp_live = client.get("/api/v1/health/liveness")
    assert resp_live.status_code == 200
    data_live = resp_live.json()
    assert data_live["status"] == "UP"
    assert data_live["service"] == "smartsalary-backend"
    assert "password" not in str(data_live).lower()
    assert "postgres" not in str(data_live).lower()

    # 2. Readiness Probe (with mock healthy dependencies)
    with patch("app.api.v1.endpoints.health.check_db_connection", return_value=True):
        resp_ready = client.get("/api/v1/health/readiness")
        assert resp_ready.status_code == 200
        data_ready = resp_ready.json()
        assert data_ready["status"] == "READY"
        assert data_ready["subsystems"]["database"] == "READY"
        assert data_ready["subsystems"]["rule_registry"] == "READY"
        assert "password" not in str(data_ready).lower()
        assert "connection" not in str(data_ready).lower()

    # 3. Readiness Probe Degraded (DB down -> 503 + telemetry emission)
    with patch("app.api.v1.endpoints.health.check_db_connection", return_value=False):
        resp_unready = client.get("/api/v1/health/readiness")
        assert resp_unready.status_code == 503
        data_unready = resp_unready.json()
        assert data_unready["status"] == "NOT_READY"
        assert data_unready["subsystems"]["database"] == "UNAVAILABLE"

        # Verify telemetry event emitted
        events = [e for e in ObservabilityService.get_events() if e.event_type == EventType.HEALTH_FAILURE]
        assert len(events) == 1
        assert events[0].severity == EventSeverity.CRITICAL
        assert events[0].safe_error_code == "ERR_SUBSYSTEM_UNREADY"
        assert events[0].details["database_ready"] is False
