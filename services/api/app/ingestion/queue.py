from typing import Any, Protocol


class IngestionQueueUnavailableError(RuntimeError):
    """Raised when a document cannot be placed on or read from the local queue."""


class IngestionQueue(Protocol):
    async def enqueue(self, *, document_id: str) -> None: ...

    async def reserve(self, *, timeout_seconds: int) -> str | None: ...

    async def complete(self, *, document_id: str) -> None: ...


class RedisIngestionQueue:
    def __init__(self, *, url: str, queue_key: str = "proofpilot:ingestion:pending") -> None:
        from redis import asyncio as redis_asyncio

        redis_factory: Any = redis_asyncio.Redis
        self._redis: Any = redis_factory.from_url(url, decode_responses=True)
        self._queue_key = queue_key
        self._processing_key = f"{queue_key}:processing"

    async def enqueue(self, *, document_id: str) -> None:
        try:
            await self._redis.lpush(self._queue_key, document_id)
        except Exception as exc:
            raise IngestionQueueUnavailableError("Unable to enqueue document processing.") from exc

    async def reserve(self, *, timeout_seconds: int) -> str | None:
        try:
            item: Any = await self._redis.brpoplpush(
                self._queue_key,
                self._processing_key,
                timeout=timeout_seconds,
            )
        except Exception as exc:
            raise IngestionQueueUnavailableError("Unable to reserve document processing.") from exc
        if item is None:
            return None
        return str(item)

    async def complete(self, *, document_id: str) -> None:
        try:
            await self._redis.lrem(self._processing_key, 1, document_id)
        except Exception as exc:
            raise IngestionQueueUnavailableError("Unable to complete document processing.") from exc

    async def recover_incomplete(self) -> None:
        try:
            while await self._redis.rpoplpush(self._processing_key, self._queue_key) is not None:
                pass
        except Exception as exc:
            raise IngestionQueueUnavailableError(
                "Unable to recover incomplete document processing."
            ) from exc

    async def close(self) -> None:
        await self._redis.aclose()
