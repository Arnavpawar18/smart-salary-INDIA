from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import ClassVar

from fastapi import Request

from app.core.limiter_exceptions import RateLimitExceeded


class InMemoryRateLimiter:
    """
    Lightweight process-local sliding window rate limiter.
    Provides protection for sensitive endpoints (login, register, change-password).
    Note: For distributed multi-instance deployment, replace with Redis-backed limiter.
    """

    _requests: ClassVar[dict[str, list[datetime]]] = defaultdict(list)

    @classmethod
    def check_rate_limit(
        cls,
        key: str,
        max_requests: int = 10,
        window_seconds: int = 60,
    ) -> None:
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=window_seconds)

        # Filter timestamps outside window
        cls._requests[key] = [ts for ts in cls._requests[key] if ts > cutoff]

        if len(cls._requests[key]) >= max_requests:
            # Calculate seconds until the oldest request expires
            oldest_ts = cls._requests[key][0]
            retry_after_seconds = max(0, int(((oldest_ts + timedelta(seconds=window_seconds)) - now).total_seconds()))
            raise RateLimitExceeded(
                retry_after=retry_after_seconds,
                limit=max_requests,
                remaining=0,
            )

        cls._requests[key].append(now)

    @classmethod
    def get_client_ip(cls, request: Request) -> str:
        if request.client:
            return request.client.host
        return "127.0.0.1"

    @classmethod
    def clear(cls) -> None:
        cls._requests.clear()
