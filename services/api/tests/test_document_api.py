from collections.abc import AsyncIterator

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.documents import get_document_service
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.vector.qdrant import QdrantCollectionConfigurationError


class MismatchedVectorCollectionService:
    async def ingest_upload(
        self,
        *,
        workspace_id: str,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> None:
        del workspace_id, filename, content_type, content
        raise QdrantCollectionConfigurationError("configured vector dimension does not match")


async def test_upload_list_and_status_for_text_document() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def test_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = test_session
    app.dependency_overrides[get_settings] = lambda: Settings(upload_indexing_enabled=False)
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
    assert uploaded["status"] == "ready"
    assert uploaded["chunk_count"] == 1

    assert list_response.status_code == 200
    assert list_response.json() == [uploaded]
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "ready"


async def test_upload_reports_vector_collection_configuration_mismatch() -> None:
    app.dependency_overrides[get_document_service] = lambda: MismatchedVectorCollectionService()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/workspaces/workspace-id/documents",
                files={"file": ("notes.md", b"# Public demo", "text/markdown")},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Document cannot be indexed with the configured vector collection."
    }
