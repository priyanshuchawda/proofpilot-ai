import os
from uuid import uuid4

import pytest

from app.ingestion.queue import RedisIngestionQueue


@pytest.mark.skipif(
    os.getenv("RUN_INFRA_INTEGRATION") != "1",
    reason="Docker-backed Redis tests are opt-in.",
)
async def test_redis_ingestion_queue_recovers_and_completes_reserved_document_job() -> None:
    queue = RedisIngestionQueue(
        url=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        queue_key=f"proofpilot:test:ingestion:{uuid4().hex}",
    )
    try:
        await queue.enqueue(document_id="document-a")

        reserved = await queue.reserve(timeout_seconds=1)
        await queue.recover_incomplete()
        recovered = await queue.reserve(timeout_seconds=1)
        await queue.complete(document_id=recovered or "")
        no_remaining_job = await queue.reserve(timeout_seconds=1)
    finally:
        await queue.close()

    assert reserved == "document-a"
    assert recovered == "document-a"
    assert no_remaining_job is None
