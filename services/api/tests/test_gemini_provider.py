import pytest

from app.ai.gemini import (
    GeminiGenerateRequest,
    GoogleGenAIProvider,
    MissingGeminiApiKeyError,
    MockGeminiProvider,
    build_gemini_provider,
)
from app.core.config import Settings


async def test_mock_gemini_provider_returns_deterministic_response() -> None:
    provider = MockGeminiProvider()

    response = await provider.generate_text(
        GeminiGenerateRequest(
            prompt="Summarize the evidence.",
            model="gemini-2.5-flash-lite",
        )
    )

    assert response.model == "gemini-2.5-flash-lite"
    assert response.text == "Mock Gemini response for: Summarize the evidence."
    assert response.provider == "mock"


def test_gemini_generate_request_can_enable_google_search_tool() -> None:
    request = GeminiGenerateRequest(
        prompt="What changed today?",
        model="gemini-2.5-flash-lite",
        enable_google_search=True,
    )

    assert request.enable_google_search


def test_provider_factory_uses_mock_when_key_missing_in_development() -> None:
    settings = Settings(gemini_api_key=None)

    provider = build_gemini_provider(settings)

    assert isinstance(provider, MockGeminiProvider)


def test_google_provider_requires_api_key() -> None:
    with pytest.raises(MissingGeminiApiKeyError):
        GoogleGenAIProvider(api_key=None)
