from collections.abc import AsyncIterator

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.query import get_query_service
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.models import Document, QueryRun, Workspace
from app.db.session import get_db_session
from app.main import app


async def test_workspace_listing_is_scoped_to_local_session_when_enabled() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def test_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = test_session
    app.dependency_overrides[get_settings] = lambda: Settings(
        proofpilot_workspace_ownership_enabled=True
    )
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            created = await client.post(
                "/api/v1/workspaces",
                headers={"X-ProofPilot-Session": "owner-a"},
                json={"name": "Owner A", "description": None},
            )
            owner_list = await client.get(
                "/api/v1/workspaces",
                headers={"X-ProofPilot-Session": "owner-a"},
            )
            other_list = await client.get(
                "/api/v1/workspaces",
                headers={"X-ProofPilot-Session": "owner-b"},
            )
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

    assert created.status_code == 201
    assert owner_list.json() == [created.json()]
    assert other_list.json() == []


async def test_document_status_is_blocked_for_cross_session_owner_when_enabled() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        workspace = Workspace(name="Private", description=None, owner_session_id="owner-a")
        session.add(workspace)
        await session.flush()
        document = Document(
            workspace_id=workspace.id,
            filename="private.md",
            mime_type="text/markdown",
            status="ready",
        )
        session.add(document)
        await session.commit()
        document_id = document.id

    async def test_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = test_session
    app.dependency_overrides[get_settings] = lambda: Settings(
        proofpilot_workspace_ownership_enabled=True
    )
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            owner_response = await client.get(
                f"/api/v1/documents/{document_id}/status",
                headers={"X-ProofPilot-Session": "owner-a"},
            )
            foreign_response = await client.get(
                f"/api/v1/documents/{document_id}/status",
                headers={"X-ProofPilot-Session": "owner-b"},
            )
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

    assert owner_response.status_code == 200
    assert foreign_response.status_code == 404


async def test_query_run_trace_is_blocked_for_cross_session_owner_when_enabled() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        workspace = Workspace(name="Private", description=None, owner_session_id="owner-a")
        session.add(workspace)
        await session.flush()
        query_run = QueryRun(
            workspace_id=workspace.id,
            query_text="private question",
            route="route_document_fast",
            mode="fast",
        )
        session.add(query_run)
        await session.commit()
        query_run_id = query_run.id

    async def test_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = test_session
    app.dependency_overrides[get_settings] = lambda: Settings(
        proofpilot_workspace_ownership_enabled=True
    )
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            owner_response = await client.get(
                f"/api/v1/query-runs/{query_run_id}",
                headers={"X-ProofPilot-Session": "owner-a"},
            )
            foreign_response = await client.get(
                f"/api/v1/query-runs/{query_run_id}",
                headers={"X-ProofPilot-Session": "owner-b"},
            )
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

    assert owner_response.status_code == 200
    assert foreign_response.status_code == 404


async def test_workspace_query_is_blocked_for_cross_session_owner_when_enabled() -> None:
    class ForbiddenQueryService:
        calls = 0

        async def answer_workspace_query(
            self,
            *,
            workspace_id: str,
            query: str,
            mode: str,
        ) -> object:
            del workspace_id, query, mode
            self.calls += 1
            raise AssertionError("foreign owner query should not reach query service")

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        workspace = Workspace(name="Private", description=None, owner_session_id="owner-a")
        session.add(workspace)
        await session.commit()
        workspace_id = workspace.id

    async def test_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    service = ForbiddenQueryService()
    app.dependency_overrides[get_db_session] = test_session
    app.dependency_overrides[get_settings] = lambda: Settings(
        proofpilot_workspace_ownership_enabled=True,
        proofpilot_rate_limiting_enabled=False,
    )
    app.dependency_overrides[get_query_service] = lambda: service
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                f"/api/v1/workspaces/{workspace_id}/query",
                headers={"X-ProofPilot-Session": "owner-b"},
                json={"query": "Can I read it?", "mode": "fast"},
            )
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

    assert response.status_code == 404
    assert service.calls == 0
