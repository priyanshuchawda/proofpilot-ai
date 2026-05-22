from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.core.config import Settings


class MissingGeminiApiKeyError(RuntimeError):
    """Raised when the real Gemini provider is requested without a backend key."""


class GeminiGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str
    response_json_schema: dict[str, Any] | None = None


class GeminiGenerateResponse(BaseModel):
    text: str
    model: str
    provider: str


class GeminiProvider(Protocol):
    async def generate_text(self, request: GeminiGenerateRequest) -> GeminiGenerateResponse: ...


class MockGeminiProvider:
    async def generate_text(self, request: GeminiGenerateRequest) -> GeminiGenerateResponse:
        return GeminiGenerateResponse(
            text=f"Mock Gemini response for: {request.prompt}",
            model=request.model,
            provider="mock",
        )


class GoogleGenAIProvider:
    def __init__(self, api_key: str | None) -> None:
        if not api_key:
            raise MissingGeminiApiKeyError("GEMINI_API_KEY is required for real Gemini calls.")
        self._api_key = api_key

    async def generate_text(self, request: GeminiGenerateRequest) -> GeminiGenerateResponse:
        from google import genai

        client = genai.Client(api_key=self._api_key)
        models: Any = client.aio.models
        config: dict[str, Any] | None = None
        if request.response_json_schema is not None:
            config = {
                "response_mime_type": "application/json",
                "response_json_schema": request.response_json_schema,
            }
        response: Any = await models.generate_content(
            model=request.model,
            contents=request.prompt,
            config=config,
        )
        return GeminiGenerateResponse(
            text=response.text or "",
            model=request.model,
            provider="google-genai",
        )


def build_gemini_provider(settings: Settings) -> GeminiProvider:
    if not settings.gemini_api_key and settings.proofpilot_env == "development":
        return MockGeminiProvider()
    return GoogleGenAIProvider(api_key=settings.gemini_api_key)
