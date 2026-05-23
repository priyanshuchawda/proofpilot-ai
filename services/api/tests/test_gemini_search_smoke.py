import os

import pytest

from app.ai.gemini import (
    GeminiGenerateRequest,
    GoogleGenAIProvider,
    choose_search_grounding_model,
)
from app.core.config import get_settings

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_GEMINI_SEARCH_SMOKE") != "1",
    reason="Real Gemini Search grounding smoke tests are opt-in only.",
)


async def test_real_gemini_search_grounding_smoke_uses_fallback_model() -> None:
    settings = get_settings()
    provider = GoogleGenAIProvider(api_key=settings.gemini_api_key)
    search_model = choose_search_grounding_model(settings)

    response = await provider.generate_text(
        GeminiGenerateRequest(
            prompt=(
                "Use Google Search if needed. Reply with one short sentence naming today's year."
            ),
            model=search_model,
            enable_google_search=True,
        )
    )

    assert response.model == search_model
    assert response.text.strip()
