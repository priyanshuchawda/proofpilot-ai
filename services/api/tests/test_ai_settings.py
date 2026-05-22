from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import app


async def test_ai_settings_report_safe_development_defaults() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(gemini_api_key=None)
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/settings/ai")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "backend_only": True,
        "gemini_configured": False,
        "generation_model": "gemini-2.5-flash-lite",
        "lightweight_model": "gemini-2.5-flash-lite",
        "freshness_model": "gemini-2.5-flash-lite",
        "embedding_model": "gemini-embedding-2",
        "search_grounding_enabled": False,
        "live_smoke_enabled": False,
    }
