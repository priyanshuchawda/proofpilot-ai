from time import monotonic
from typing import Any, Protocol, cast


class CacheBackend(Protocol):
    async def get_json(self, key: str) -> dict[str, Any] | None: ...

    async def set_json(
        self,
        key: str,
        value: dict[str, Any],
        *,
        ttl_seconds: int,
    ) -> None: ...


class InMemoryCacheBackend:
    def __init__(self) -> None:
        self.values: dict[str, tuple[dict[str, Any], float]] = {}

    async def get_json(self, key: str) -> dict[str, Any] | None:
        cached = self.values.get(key)
        if cached is None:
            return None
        value, expires_at = cached
        if expires_at <= monotonic():
            self.values.pop(key, None)
            return None
        return value

    async def set_json(
        self,
        key: str,
        value: dict[str, Any],
        *,
        ttl_seconds: int,
    ) -> None:
        self.values[key] = (value, monotonic() + ttl_seconds)


class RedisCacheBackend:
    def __init__(self, *, url: str) -> None:
        from redis import asyncio as redis_asyncio

        redis_factory: Any = redis_asyncio.Redis
        self._redis: Any = redis_factory.from_url(url, decode_responses=True)

    async def get_json(self, key: str) -> dict[str, Any] | None:
        import json

        raw = await self._redis.get(key)
        if raw is None:
            return None
        value: Any = json.loads(raw)
        if not isinstance(value, dict):
            return None
        return cast(dict[str, Any], value)

    async def set_json(
        self,
        key: str,
        value: dict[str, Any],
        *,
        ttl_seconds: int,
    ) -> None:
        import json

        await self._redis.set(key, json.dumps(value), ex=ttl_seconds)

    async def close(self) -> None:
        await self._redis.aclose()
