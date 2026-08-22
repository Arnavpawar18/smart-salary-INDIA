import pytest
from fastapi import Request

from app.core.config import rate_limit_settings
from app.core.limiter import RateLimiter
from app.core.limiter_exceptions import RateLimitExceeded


# Helper to create a minimal Request with a client IP
def make_request(client_ip: str = "127.0.0.1") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "client": (client_ip, 12345),
    }
    return Request(scope)

@pytest.fixture(autouse=True)
def reset_inmemory_rate_limiter(monkeypatch):
    # Ensure Redis is not required for these core tests
    monkeypatch.setattr(rate_limit_settings, "RATE_LIMIT_REDIS_REQUIRED", False)
    monkeypatch.setattr(rate_limit_settings, "REDIS_URL", None)
    # Clear any leftover state in InMemoryRateLimiter
    from app.core.rate_limiter import InMemoryRateLimiter
    InMemoryRateLimiter._requests.clear()
    yield
    InMemoryRateLimiter._requests.clear()

@pytest.mark.asyncio
async def test_rate_limiter_uses_inmemory_and_enforces_limit(monkeypatch):
    # Set a low limit for testing
    monkeypatch.setattr(rate_limit_settings, "CALC_RATE_LIMIT", 2)
    monkeypatch.setattr(rate_limit_settings, "CALC_RATE_WINDOW", 60)
    request = make_request()
    # First request should pass
    await RateLimiter.check_rate_limit(
        request,
        max_requests=rate_limit_settings.CALC_RATE_LIMIT,
        window_seconds=rate_limit_settings.CALC_RATE_WINDOW,
        key_prefix="test",
    )
    # Second request should also pass
    await RateLimiter.check_rate_limit(
        request,
        max_requests=rate_limit_settings.CALC_RATE_LIMIT,
        window_seconds=rate_limit_settings.CALC_RATE_WINDOW,
        key_prefix="test",
    )
    # Third request should raise RateLimitExceeded
    with pytest.raises(RateLimitExceeded):
        await RateLimiter.check_rate_limit(
            request,
            max_requests=rate_limit_settings.CALC_RATE_LIMIT,
            window_seconds=rate_limit_settings.CALC_RATE_WINDOW,
            key_prefix="test",
        )
