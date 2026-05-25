from collections.abc import AsyncIterator

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.services.evaluations import get_evals_results_dir


async def test_evaluation_run_and_metrics_summary_endpoints() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def test_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = test_session
    app.dependency_overrides[get_settings] = lambda: Settings(
        proofpilot_rate_limiting_enabled=False
    )
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            run_response = await client.post("/api/v1/evaluations/run")
            run_payload = run_response.json()
            get_response = await client.get(f"/api/v1/evaluations/runs/{run_payload['run_id']}")
            metrics_response = await client.get("/api/v1/metrics/summary")
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

    assert run_response.status_code == 201
    assert run_payload["status"] == "completed"
    assert run_payload["summary"]["case_count"] >= 6
    assert get_response.status_code == 200
    assert get_response.json()["run_id"] == run_payload["run_id"]
    assert metrics_response.status_code == 200
    assert "latency_p95_ms" in metrics_response.json()
    assert (get_evals_results_dir() / f"{run_payload['run_id']}.json").exists()
