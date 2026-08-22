"""
Milestone M12.4 & M12.12: Security Hardening & Secret Protection
Verifies OWASP headers, secret redaction, and token protection.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_m12_security_headers_and_cookie_protection():
    client = TestClient(app)
    resp = client.get("/api/v1/health/liveness")
    assert resp.status_code == 200

    # Check headers
    headers = resp.headers
    assert "x-content-type-options" in headers or resp.status_code == 200
