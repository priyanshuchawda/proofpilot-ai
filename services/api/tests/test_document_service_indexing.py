from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import Workspace
from app.services.documents import DocumentService


class FakeDocumentIndexer:
    def __init__(self) -> None:
        self.document_ids: list[str] = []

    async def index_document(self, *, document_id: str) -> int:
        self.document_ids.append(document_id)
        return 1


async def test_document_service_indexes_document_after_chunks_are_ready(tmp_path: Path) -> None:
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

        document = await service.ingest_upload(
            workspace_id=workspace.id,
            filename="notes.md",
            content_type="text/markdown",
            content=b"# Demo\nProofPilot stores grounded evidence.",
        )

    await engine.dispose()

    assert document.status == "ready"
    assert indexer.document_ids == [document.id]
