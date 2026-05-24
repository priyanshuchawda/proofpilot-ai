from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import IngestionJob, Workspace
from app.services.documents import DocumentService


class FakeDocumentIndexer:
    def __init__(self) -> None:
        self.document_ids: list[str] = []

    async def index_document(self, *, document_id: str) -> int:
        self.document_ids.append(document_id)
        return 1


class FailingDocumentIndexer:
    async def index_document(self, *, document_id: str) -> int:
        del document_id
        raise RuntimeError("internal indexing failure with sensitive context")


class InterruptedDocumentIndexer:
    async def index_document(self, *, document_id: str) -> int:
        del document_id
        raise KeyboardInterrupt("worker exited after chunk persistence")


async def test_document_service_accepts_upload_before_processing_and_indexing(
    tmp_path: Path,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        workspace = Workspace(name="Docs", description=None)
        session.add(workspace)
        await session.commit()

        indexer = FakeDocumentIndexer()
        service = DocumentService(
            session,
            tmp_path,
            document_indexer=indexer,
        )

        document = await service.create_upload(
            workspace_id=workspace.id,
            filename="notes.md",
            content_type="text/markdown",
            content=b"# Demo\nProofPilot stores grounded evidence.",
        )

        assert document.status == "uploaded"
        assert indexer.document_ids == []

        document = await service.process_document(document_id=document.id)

    await engine.dispose()

    assert document.status == "ready"
    assert indexer.document_ids == [document.id]


async def test_document_service_records_safe_failed_status_when_processing_fails(
    tmp_path: Path,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        workspace = Workspace(name="Docs", description=None)
        session.add(workspace)
        await session.commit()
        service = DocumentService(session, tmp_path, document_indexer=FailingDocumentIndexer())
        document = await service.create_upload(
            workspace_id=workspace.id,
            filename="notes.md",
            content_type="text/markdown",
            content=b"# Demo\nPublic processing content.",
        )

        failed = await service.process_document(document_id=document.id)
        job = (await session.execute(select(IngestionJob))).scalar_one()

    await engine.dispose()

    assert failed.status == "failed"
    assert job.status == "failed"
    assert job.error_message == "Document processing failed."


async def test_document_service_resumes_chunked_document_after_worker_interruption(
    tmp_path: Path,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        workspace = Workspace(name="Docs", description=None)
        session.add(workspace)
        await session.commit()
        interrupted_service = DocumentService(
            session,
            tmp_path,
            document_indexer=InterruptedDocumentIndexer(),
        )
        document = await interrupted_service.create_upload(
            workspace_id=workspace.id,
            filename="notes.md",
            content_type="text/markdown",
            content=b"# Demo\nPublic processing content.",
        )

        with pytest.raises(KeyboardInterrupt, match="worker exited"):
            await interrupted_service.process_document(document_id=document.id)

        assert document.status == "chunked"
        assert await interrupted_service.chunk_count(document_id=document.id) == 1

        indexer = FakeDocumentIndexer()
        resumed_service = DocumentService(session, tmp_path, document_indexer=indexer)
        resumed = await resumed_service.process_document(document_id=document.id)

        assert resumed.status == "ready"
        assert await resumed_service.chunk_count(document_id=document.id) == 1
        assert indexer.document_ids == [document.id]

    await engine.dispose()
