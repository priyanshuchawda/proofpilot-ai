from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import app


async def test_ai_settings_report_safe_development_defaults() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        gemini_api_key=None,
        gemini_generation_model="gemini-3.1-flash-lite",
        gemini_lightweight_model="gemini-2.5-flash-lite",
        gemini_fresh_model="gemini-3.1-flash-lite",
        gemini_search_grounding_fallback_model="gemini-2.5-flash-lite",
        gemini_embeddings_enabled=False,
    )
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
        "generation_model": "gemini-3.1-flash-lite",
        "lightweight_model": "gemini-2.5-flash-lite",
        "freshness_model": "gemini-3.1-flash-lite",
        "search_grounding_model": "gemini-2.5-flash-lite",
        "embedding_model": "gemini-embedding-2",
        "embedding_dimension": 768,
        "embeddings_enabled": False,
        "search_grounding_enabled": False,
        "live_smoke_enabled": False,
    }
