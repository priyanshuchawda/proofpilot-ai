from collections.abc import AsyncIterator
from hashlib import sha256
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.main import app
from app.security.rate_limiting import (
    RateLimiter,
    RateLimiterUnavailableError,
    RateLimitExceededError,
    RedisRateLimiter,
    get_rate_limiter,
)


class ScriptRedis:
    def __init__(
        self, results: list[list[int]] | None = None, error: Exception | None = None
    ) -> None:
        self.results = results or []
        self.error = error
        self.calls: list[tuple[str, int, str, int, int]] = []

    async def eval(
        self,
        script: str,
        key_count: int,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> list[int]:
        self.calls.append((script, key_count, key, limit, window_seconds))
        if self.error is not None:
            raise self.error
        return self.results.pop(0)

    async def aclose(self) -> None:
        return None


class RejectingRateLimiter:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls: list[tuple[str, str, int, int]] = []

    async def enforce(
        self,
        *,
        bucket: str,
        client_identifier: str,
        limit: int,
        window_seconds: int,
    ) -> None:
        self.calls.append((bucket, client_identifier, limit, window_seconds))
        raise self.error


async def test_redis_rate_limiter_hashes_client_identifier_and_enforces_window() -> None:
    redis = ScriptRedis(results=[[1, 60], [2, 42]])
    limiter = RedisRateLimiter(redis_client=redis)

    await limiter.enforce(
        bucket="sensitive",
        client_identifier="203.0.113.21",
        limit=1,
        window_seconds=60,
    )
    with pytest.raises(RateLimitExceededError) as exceeded:
        await limiter.enforce(
            bucket="sensitive",
            client_identifier="203.0.113.21",
            limit=1,
            window_seconds=60,
        )

    expected_digest = sha256(b"203.0.113.21").hexdigest()
    assert redis.calls[0][2] == f"proofpilot:rate-limit:sensitive:{expected_digest}"
    assert "203.0.113.21" not in redis.calls[0][2]
    assert exceeded.value.retry_after_seconds == 42


async def test_redis_rate_limiter_normalizes_backend_failure() -> None:
    limiter = RedisRateLimiter(redis_client=ScriptRedis(error=ConnectionError("redis unavailable")))

    with pytest.raises(RateLimiterUnavailableError):
        await limiter.enforce(
            bucket="sensitive",
            client_identifier="203.0.113.22",
            limit=5,
            window_seconds=60,
        )


@pytest.mark.parametrize(
    ("path", "request_kwargs"),
    [
        ("/api/v1/workspaces/workspace-a/query", {"json": {"query": "Question?"}}),
        ("/api/v1/workspaces/workspace-a/query/stream", {"json": {"query": "Question?"}}),
        (
            "/api/v1/workspaces/workspace-a/documents",
            {"files": {"file": ("public.md", b"# Public", "text/markdown")}},
        ),
        ("/api/v1/evaluations/run", {}),
    ],
)
async def test_sensitive_routes_return_retry_after_when_budget_is_exhausted(
    path: str,
    request_kwargs: dict[str, Any],
) -> None:
    limiter = RejectingRateLimiter(RateLimitExceededError(retry_after_seconds=37))

    async def override_limiter() -> AsyncIterator[RateLimiter]:
        yield limiter

    app.dependency_overrides[get_rate_limiter] = override_limiter
    app.dependency_overrides[get_settings] = lambda: Settings(
        proofpilot_rate_limiting_enabled=True,
        proofpilot_rate_limit_sensitive_requests=3,
        proofpilot_rate_limit_window_seconds=60,
    )
    transport = ASGITransport(app=app, client=("203.0.113.9", 4567), raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(path, **request_kwargs)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 429
    assert response.headers["retry-after"] == "37"
    assert response.json() == {"detail": "Request limit exceeded. Try again later."}
    assert limiter.calls == [("sensitive", "203.0.113.9", 3, 60)]


async def test_sensitive_route_fails_closed_when_limiter_is_unavailable() -> None:
    limiter = RejectingRateLimiter(RateLimiterUnavailableError())

    async def override_limiter() -> AsyncIterator[RateLimiter]:
        yield limiter

    app.dependency_overrides[get_rate_limiter] = override_limiter
    app.dependency_overrides[get_settings] = lambda: Settings(proofpilot_rate_limiting_enabled=True)
    transport = ASGITransport(app=app, client=("203.0.113.10", 4567), raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/workspaces/workspace-a/query",
                json={"query": "Question?"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Request protection unavailable. Try again later."}


def test_rate_limit_settings_require_positive_limits() -> None:
    with pytest.raises(ValidationError):
        Settings(proofpilot_rate_limit_sensitive_requests=0)
    with pytest.raises(ValidationError):
        Settings(proofpilot_rate_limit_window_seconds=0)
