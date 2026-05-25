from collections.abc import AsyncIterator
from hashlib import sha256
from typing import Annotated, Any, Protocol, cast

from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings


class RateLimitExceededError(Exception):
    def __init__(self, *, retry_after_seconds: int) -> None:
        super().__init__("rate limit exceeded")
        self.retry_after_seconds = retry_after_seconds


class RateLimiterUnavailableError(Exception):
    pass


class RateLimiter(Protocol):
    async def enforce(
        self,
        *,
        bucket: str,
        client_identifier: str,
        limit: int,
        window_seconds: int,
    ) -> None: ...


class DisabledRateLimiter:
    async def enforce(
        self,
        *,
        bucket: str,
        client_identifier: str,
        limit: int,
        window_seconds: int,
    ) -> None:
        del bucket, client_identifier, limit, window_seconds


class RedisRateLimiter:
    _SCRIPT = """
local current = redis.call("INCR", KEYS[1])
if current == 1 then
  redis.call("EXPIRE", KEYS[1], ARGV[2])
end
local ttl = redis.call("TTL", KEYS[1])
return { current, ttl }
"""

    def __init__(self, *, redis_client: Any) -> None:
        self._redis = redis_client

    @classmethod
    def from_url(cls, url: str) -> "RedisRateLimiter":
        from redis import asyncio as redis_asyncio

        redis_factory: Any = redis_asyncio.Redis
        return cls(redis_client=redis_factory.from_url(url, decode_responses=True))

    async def enforce(
        self,
        *,
        bucket: str,
        client_identifier: str,
        limit: int,
        window_seconds: int,
    ) -> None:
        key = _rate_limit_key(bucket=bucket, client_identifier=client_identifier)
        try:
            raw_result = await self._redis.eval(self._SCRIPT, 1, key, limit, window_seconds)
        except Exception as exc:
            raise RateLimiterUnavailableError() from exc

        result = cast(list[Any], raw_result)
        current = int(result[0])
        ttl = max(1, int(result[1]))
        if current > limit:
            raise RateLimitExceededError(retry_after_seconds=ttl)

    async def close(self) -> None:
        await self._redis.aclose()


async def get_rate_limiter(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[RateLimiter]:
    if not settings.proofpilot_rate_limiting_enabled:
        yield DisabledRateLimiter()
        return

    limiter = RedisRateLimiter.from_url(settings.redis_url)
    try:
        yield limiter
    finally:
        await limiter.close()


async def enforce_sensitive_rate_limit(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> None:
    if not settings.proofpilot_rate_limiting_enabled:
        return
    client_identifier = request.client.host if request.client else "unknown"
    try:
        await limiter.enforce(
            bucket="sensitive",
            client_identifier=client_identifier,
            limit=settings.proofpilot_rate_limit_sensitive_requests,
            window_seconds=settings.proofpilot_rate_limit_window_seconds,
        )
    except RateLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Request limit exceeded. Try again later.",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except RateLimiterUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Request protection unavailable. Try again later.",
        ) from exc


def _rate_limit_key(*, bucket: str, client_identifier: str) -> str:
    digest = sha256(client_identifier.encode("utf-8")).hexdigest()
    return f"proofpilot:rate-limit:{bucket}:{digest}"
