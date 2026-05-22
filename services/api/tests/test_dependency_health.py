from httpx import ASGITransport, AsyncClient

from app.infra.health import DependencyHealth, get_dependency_health_checker
from app.main import app


async def test_dependency_health_endpoint_reports_configured_services() -> None:
    async def fake_health_checker() -> list[DependencyHealth]:
        return [
            DependencyHealth(name="postgres", status="ok"),
            DependencyHealth(name="redis", status="ok"),
            DependencyHealth(name="qdrant", status="ok"),
        ]

    app.dependency_overrides[get_dependency_health_checker] = lambda: fake_health_checker
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/health/dependencies")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "services": [
            {"name": "postgres", "status": "ok", "detail": None},
            {"name": "redis", "status": "ok", "detail": None},
            {"name": "qdrant", "status": "ok", "detail": None},
        ]
    }
