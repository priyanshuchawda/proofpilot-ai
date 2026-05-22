from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health_endpoint_reports_service_status() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "proofpilot-api",
        "status": "ok",
        "version": "0.1.0",
    }
