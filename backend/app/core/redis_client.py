import redis.asyncio as redis

from app.core.config import rate_limit_settings


class RedisClient:
    _client: redis.Redis | None = None

    @classmethod
    async def get_client(cls) -> redis.Redis | None:
        """Return a Redis client instance respecting configuration.

        - If ``RATE_LIMIT_REDIS_REQUIRED`` is ``True`` and ``REDIS_URL`` is missing,
          a clear ``RuntimeError`` is raised.
        - If ``RATE_LIMIT_REDIS_REQUIRED`` is ``False`` and ``REDIS_URL`` is missing,
          the method returns ``None`` allowing the application to start without Redis.
        - When a URL is provided, a client is created as before.
        """
        if cls._client is None:
            # Redis is required for production rate‑limiting
            if rate_limit_settings.RATE_LIMIT_REDIS_REQUIRED:
                if not rate_limit_settings.REDIS_URL:
                    raise RuntimeError(
                        "REDIS_URL is not configured but rate limiting requires Redis."
                    )
            # If not required and URL missing, skip initialization
            if not rate_limit_settings.REDIS_URL:
                return None
            cls._client = redis.from_url(
                str(rate_limit_settings.REDIS_URL),
                socket_timeout=rate_limit_settings.REDIS_TIMEOUT_SECONDS,
            )
        return cls._client

    @classmethod
    async def close(cls) -> None:
        if cls._client is not None:
            await cls._client.close()
            cls._client = None

# FastAPI lifespan integration helper (optional usage)
async def redis_lifespan(app):
    """FastAPI lifespan hook that attaches a Redis client to ``app.state``.

    The client may be ``None`` when Redis is optional (e.g., during local
    development or tests). In that case the attribute is simply omitted.
    """
    client = await RedisClient.get_client()
    if client is not None:
        app.state.redis = client

    # Startup SMTP connectivity check
    if getattr(rate_limit_settings, "ENABLE_STARTUP_SMTP_CHECK", True):
        from app.services.email_service import EmailService
        EmailService.check_connectivity()

    try:
        yield
    finally:
        if client is not None:
            await RedisClient.close()
