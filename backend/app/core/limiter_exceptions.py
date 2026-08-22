"""Rate limiting related exception definitions."""

from fastapi import HTTPException
from starlette.status import HTTP_429_TOO_MANY_REQUESTS


class RateLimitExceeded(HTTPException):
    """Exception raised when a client exceeds the allowed rate limit.

    Attributes:
        retry_after (int): Seconds the client should wait before retrying.
        limit (int): The maximum number of requests allowed in the window.
        remaining (int): Number of remaining requests in the current window (typically 0 when raised).
    """

    def __init__(self, *, retry_after: int, limit: int, remaining: int = 0, detail: str = "Rate limit exceeded"):
        headers = {"Retry-After": str(retry_after), "X-RateLimit-Limit": str(limit), "X-RateLimit-Remaining": str(remaining)}
        super().__init__(status_code=HTTP_429_TOO_MANY_REQUESTS, detail=detail, headers=headers)
