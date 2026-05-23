import os
from uuid import uuid4

import pytest

from app.cache.backends import RedisCacheBackend


@pytest.mark.skipif(
    os.getenv("RUN_INFRA_INTEGRATION") != "1",
    reason="Docker-backed Redis tests are opt-in.",
)
async def test_redis_cache_backend_round_trips_json_with_ttl() -> None:
    cache = RedisCacheBackend(url=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    key = f"proofpilot:test:{uuid4().hex}"
    try:
        await cache.set_json(key, {"value": "cached"}, ttl_seconds=30)

        assert await cache.get_json(key) == {"value": "cached"}
    finally:
        await cache.close()
