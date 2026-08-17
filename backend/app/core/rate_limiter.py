from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import ClassVar

from fastapi import HTTPException, Request, status


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
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please wait a moment before trying again.",
            )

        cls._requests[key].append(now)

    @classmethod
    def get_client_ip(cls, request: Request) -> str:
        if request.client:
            return request.client.host
        return "127.0.0.1"
