from collections.abc import AsyncIterator

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app


async def test_create_and_list_workspaces() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def test_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = test_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            create_response = await client.post(
                "/api/v1/workspaces",
                json={"name": "Demo Workspace", "description": "Public demo documents"},
            )
            list_response = await client.get("/api/v1/workspaces")
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Demo Workspace"
    assert created["description"] == "Public demo documents"
    assert created["id"]

    assert list_response.status_code == 200
    assert list_response.json() == [created]
