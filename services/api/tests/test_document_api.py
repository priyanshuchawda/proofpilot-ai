from collections.abc import AsyncIterator

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.documents import get_document_service, get_ingestion_queue
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.models import Document
from app.db.session import get_db_session
from app.ingestion.queue import IngestionQueueUnavailableError
from app.main import app


class FakeIngestionQueue:
    def __init__(self) -> None:
        self.document_ids: list[str] = []

    async def enqueue(self, *, document_id: str) -> None:
        self.document_ids.append(document_id)


class UnavailableIngestionQueue:
    async def enqueue(self, *, document_id: str) -> None:
        del document_id
        raise IngestionQueueUnavailableError("Redis connection failed")


class AcceptedDocumentService:
    def __init__(self) -> None:
        self.failed_ids: list[str] = []

    async def create_upload(
        self,
        *,
        workspace_id: str,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> Document:
        del content
        return Document(
            id="document-id",
            workspace_id=workspace_id,
            filename=filename,
            mime_type=content_type or "application/octet-stream",
            status="uploaded",
        )

    async def mark_failed(self, *, document_id: str) -> None:
        self.failed_ids.append(document_id)


async def test_upload_list_and_status_for_text_document() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def test_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = test_session
    app.dependency_overrides[get_settings] = lambda: Settings(
        proofpilot_rate_limiting_enabled=False,
        upload_indexing_enabled=False,
    )
    queue = FakeIngestionQueue()
    app.dependency_overrides[get_ingestion_queue] = lambda: queue
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            workspace = (
                await client.post("/api/v1/workspaces", json={"name": "Docs", "description": None})
            ).json()
            upload_response = await client.post(
                f"/api/v1/workspaces/{workspace['id']}/documents",
                files={
                    "file": ("notes.md", b"# Demo\nThis is public demo content.", "text/markdown")
                },
            )
            list_response = await client.get(f"/api/v1/workspaces/{workspace['id']}/documents")
            uploaded = upload_response.json()
            status_response = await client.get(f"/api/v1/documents/{uploaded['id']}/status")
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

    assert upload_response.status_code == 201
    assert uploaded["filename"] == "notes.md"
    assert uploaded["status"] == "uploaded"
    assert uploaded["chunk_count"] == 0
    assert queue.document_ids == [uploaded["id"]]

    assert list_response.status_code == 200
    assert list_response.json() == [uploaded]
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "uploaded"


async def test_upload_reports_queue_unavailability_without_internal_details() -> None:
    service = AcceptedDocumentService()
    app.dependency_overrides[get_document_service] = lambda: service
    app.dependency_overrides[get_ingestion_queue] = lambda: UnavailableIngestionQueue()
    app.dependency_overrides[get_settings] = lambda: Settings(
        proofpilot_rate_limiting_enabled=False
    )
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/workspaces/workspace-id/documents",
                files={"file": ("notes.md", b"# Public demo", "text/markdown")},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Document processing queue is unavailable. Try again later."
    }
    assert service.failed_ids == ["document-id"]
