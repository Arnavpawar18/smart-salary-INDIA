"""Redis-backed rate limiting core implementation.

Provides a production-ready rate limiter using a Redis sliding window algorithm.
It mirrors the InMemoryRateLimiter API but stores request timestamps in Redis.
"""

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import Request

from app.core.config import rate_limit_settings
from app.core.limiter_exceptions import RateLimitExceeded
from app.core.redis_client import RedisClient


class RedisRateLimiter:
    """Redis‑backed sliding‑window rate limiter.

    The limiter stores a sorted set per key with timestamps (as scores).
    On each request we prune entries older than the window and check the count.
    If the limit is exceeded, a :class:`RateLimitExceeded` is raised.
    """

    @classmethod
    async def _get_redis(cls) -> Any:
        """Retrieve the singleton Redis client.

        Returns the ``redis.asyncio`` client instance.
        """
        return await RedisClient.get_client()

    @classmethod
    async def _make_key(cls, key: str) -> str:
        """Build a versioned Redis key.

        The key is prefixed with the environment (development / test / production)
        to avoid collisions across deployments.
        """
        env = rate_limit_settings.ENVIRONMENT
        return f"rate_limit:{env}:{key}"

    @classmethod
    async def check_rate_limit(
        cls,
        request: Request,
        *,
        max_requests: int,
        window_seconds: int,
        key_prefix: str = "",
    ) -> None:
        """Enforce the rate‑limit for the given request.

        Parameters
        ----------
        request: Request
            FastAPI request object – used to extract the client IP.
        max_requests: int
            Maximum allowed requests within the window.
        window_seconds: int
            Length of the sliding window in seconds.
        key_prefix: str, optional
            Optional prefix to distinguish different operation buckets.
        """
        client_ip = cls.get_client_ip(request)
        raw_key = f"{key_prefix}:{client_ip}" if key_prefix else client_ip
        redis_key = await cls._make_key(raw_key)
        redis = await cls._get_redis()

        now = datetime.now(UTC).timestamp()
        cutoff = now - window_seconds

        # Remove stale entries
        await redis.zremrangebyscore(redis_key, 0, cutoff)
        # Add current request timestamp
        await redis.zadd(redis_key, {json.dumps(now): now})
        # Set an expiry slightly longer than the window to prune keys over time
        await redis.expire(redis_key, window_seconds * 2)

        # Count entries in the current window
        count = await redis.zcard(redis_key)
        if count > max_requests:
            # Calculate retry after based on oldest timestamp in the window
            oldest = await redis.zrange(redis_key, 0, 0, withscores=True)
            if oldest:
                retry_after = int(oldest[0][1] + window_seconds - now)
            else:
                retry_after = window_seconds
            raise RateLimitExceeded(
                retry_after=retry_after,
                limit=max_requests,
                remaining=0,
                detail="Rate limit exceeded",
            )

    @staticmethod
    def get_client_ip(request: Request) -> str:
        """Extract the client IP from the request.

        FastAPI's ``request.client`` provides the remote address.
        If unavailable, fall back to a placeholder.
        """
        if request.client:
            return request.client.host
        return "127.0.0.1"
