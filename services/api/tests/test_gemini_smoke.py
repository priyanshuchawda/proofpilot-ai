import os

import pytest

from app.ai.gemini import GeminiGenerateRequest, GoogleGenAIProvider
from app.core.config import get_settings


@pytest.mark.skipif(
    os.getenv("RUN_GEMINI_SMOKE") != "1",
    reason="Real Gemini smoke tests are opt-in only.",
)
async def test_real_gemini_flash_lite_smoke() -> None:
    settings = get_settings()
    provider = GoogleGenAIProvider(api_key=settings.gemini_api_key)

    response = await provider.generate_text(
        GeminiGenerateRequest(
            prompt="Reply with exactly: proofpilot-smoke-ok",
            model="gemini-2.5-flash-lite",
        )
    )

    assert "proofpilot-smoke-ok" in response.text.lower()
    assert response.model == "gemini-2.5-flash-lite"
