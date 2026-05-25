import os
from uuid import uuid4

import pytest

from app.security.rate_limiting import RateLimitExceededError, RedisRateLimiter


@pytest.mark.skipif(
    os.getenv("RUN_INFRA_INTEGRATION") != "1",
    reason="Docker-backed Redis tests are opt-in.",
)
async def test_redis_rate_limiter_rejects_second_request_in_same_window() -> None:
    limiter = RedisRateLimiter.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    bucket = f"integration-{uuid4().hex}"
    try:
        await limiter.enforce(
            bucket=bucket,
            client_identifier="local-test-client",
            limit=1,
            window_seconds=10,
        )

        with pytest.raises(RateLimitExceededError):
            await limiter.enforce(
                bucket=bucket,
                client_identifier="local-test-client",
                limit=1,
                window_seconds=10,
            )
    finally:
        await limiter.close()
