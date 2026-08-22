"""RateLimiter facade that selects RedisRateLimiter or InMemoryRateLimiter based on configuration."""

from fastapi import Request

from app.core.config import rate_limit_settings
from app.core.rate_limiter import InMemoryRateLimiter
from app.core.redis_rate_limiter import RedisRateLimiter


class RateLimiter:
    """Facade for rate limiting.

    Uses RedisRateLimiter when RATE_LIMIT_REDIS_REQUIRED is True, otherwise falls back to InMemoryRateLimiter.
    """

    @classmethod
    async def check_rate_limit(
        cls,
        request: Request,
        *,
        max_requests: int,
        window_seconds: int,
        key_prefix: str = "",
    ) -> None:
        """Enforce rate limit using the appropriate backend.

        Parameters are forwarded to the underlying implementation.
        """
        if rate_limit_settings.RATE_LIMIT_REDIS_REQUIRED:
            await RedisRateLimiter.check_rate_limit(
                request,
                max_requests=max_requests,
                window_seconds=window_seconds,
                key_prefix=key_prefix,
            )
        else:
            client_ip = InMemoryRateLimiter.get_client_ip(request)
            key = f"{key_prefix}:{client_ip}" if key_prefix else client_ip
            InMemoryRateLimiter.check_rate_limit(
                key,
                max_requests=max_requests,
                window_seconds=window_seconds,
            )

    @staticmethod
    def get_client_ip(request: Request) -> str:
        """Utility to extract client IP (delegated to InMemoryRateLimiter)."""
        return InMemoryRateLimiter.get_client_ip(request)
