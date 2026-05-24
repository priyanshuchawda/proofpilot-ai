import pytest

from app.ingestion.worker import process_next_job


class FakeQueue:
    def __init__(self, document_id: str | None) -> None:
        self._document_id = document_id
        self.completed_ids: list[str] = []

    async def enqueue(self, *, document_id: str) -> None:
        self._document_id = document_id

    async def reserve(self, *, timeout_seconds: int) -> str | None:
        assert timeout_seconds == 1
        return self._document_id

    async def complete(self, *, document_id: str) -> None:
        self.completed_ids.append(document_id)


class FakeProcessor:
    def __init__(self) -> None:
        self.document_ids: list[str] = []

    async def process_document(self, *, document_id: str) -> None:
        self.document_ids.append(document_id)


async def test_process_next_job_processes_reserved_document() -> None:
    queue = FakeQueue("document-a")
    processor = FakeProcessor()

    processed = await process_next_job(
        queue=queue,
        processor=processor,
        timeout_seconds=1,
    )

    assert processed is True
    assert processor.document_ids == ["document-a"]
    assert queue.completed_ids == ["document-a"]


async def test_process_next_job_returns_false_when_queue_is_empty() -> None:
    queue = FakeQueue(None)
    processor = FakeProcessor()

    processed = await process_next_job(
        queue=queue,
        processor=processor,
        timeout_seconds=1,
    )

    assert processed is False
    assert processor.document_ids == []
    assert queue.completed_ids == []


class FailingProcessor:
    async def process_document(self, *, document_id: str) -> None:
        raise RuntimeError(f"worker stopped while processing {document_id}")


async def test_process_next_job_leaves_unfinished_document_unacknowledged() -> None:
    queue = FakeQueue("document-a")

    with pytest.raises(RuntimeError, match="worker stopped"):
        await process_next_job(
            queue=queue,
            processor=FailingProcessor(),
            timeout_seconds=1,
        )

    assert queue.completed_ids == []
