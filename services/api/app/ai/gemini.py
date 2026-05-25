import json
import re
from collections.abc import Mapping
from typing import Any, Protocol, cast

from pydantic import BaseModel, Field

from app.core.config import Settings

FREE_TIER_SEARCH_GROUNDING_MODELS = frozenset(
    {
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash-lite-preview-09-2025",
    }
)


class MissingGeminiApiKeyError(RuntimeError):
    """Raised when the real Gemini provider is requested without a backend key."""


class GeminiProviderUnavailableError(RuntimeError):
    """Raised for retriable quota exhaustion or temporary provider unavailability."""

    def __init__(self, *, status_code: int) -> None:
        super().__init__(f"Gemini request unavailable with status {status_code}.")
        self.status_code = status_code


class GeminiGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str
    response_json_schema: dict[str, Any] | None = None
    enable_google_search: bool = False


class GeminiGroundingSource(BaseModel):
    citation_label: str
    title: str
    uri: str
    evidence_text: str


def empty_grounding_sources() -> list[GeminiGroundingSource]:
    return []


class GeminiGenerateResponse(BaseModel):
    text: str
    model: str
    provider: str
    grounding_sources: list[GeminiGroundingSource] = Field(default_factory=empty_grounding_sources)
    search_suggestions_html: str | None = None


class GeminiProvider(Protocol):
    async def generate_text(self, request: GeminiGenerateRequest) -> GeminiGenerateResponse: ...


class MockGeminiProvider:
    async def generate_text(self, request: GeminiGenerateRequest) -> GeminiGenerateResponse:
        if request.response_json_schema is not None:
            chunk_id = _first_prompt_chunk_id(request.prompt)
            payload = {
                "answer_text": (
                    f"Mock cited answer based on evidence [{chunk_id}]." if chunk_id else ""
                ),
                "citation_chunk_ids": [chunk_id] if chunk_id else [],
            }
            return GeminiGenerateResponse(
                text=json.dumps(payload, separators=(",", ":")),
                model=request.model,
                provider="mock",
            )
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
        from google.genai import types

        models: Any = client.aio.models
        config: dict[str, Any] | None = None
        config_values: dict[str, Any] = {}
        if request.response_json_schema is not None:
            config_values["response_mime_type"] = "application/json"
            config_values["response_json_schema"] = request.response_json_schema
        if request.enable_google_search:
            config_values["tools"] = [
                types.Tool(google_search=types.GoogleSearch()),
            ]
        if config_values:
            config = config_values
        try:
            response: Any = await models.generate_content(
                model=request.model,
                contents=request.prompt,
                config=config,
            )
        except Exception as error:
            unavailable_error = normalize_gemini_unavailable_error(error)
            if unavailable_error is not None:
                raise unavailable_error from error
            raise
        text = response.text or ""
        if request.enable_google_search:
            text = insert_web_citation_labels(text, response)
        return GeminiGenerateResponse(
            text=text,
            model=request.model,
            provider="google-genai",
            grounding_sources=extract_web_grounding_sources(response),
            search_suggestions_html=extract_search_suggestions_html(response),
        )


def build_gemini_provider(settings: Settings) -> GeminiProvider:
    if settings.gemini_provider_mode == "mock":
        return MockGeminiProvider()
    if settings.gemini_provider_mode == "google":
        return GoogleGenAIProvider(api_key=settings.gemini_api_key)
    if not settings.gemini_api_key and settings.proofpilot_env == "development":
        return MockGeminiProvider()
    return GoogleGenAIProvider(api_key=settings.gemini_api_key)


def is_free_tier_search_grounding_model(model: str) -> bool:
    return model in FREE_TIER_SEARCH_GROUNDING_MODELS


def choose_search_grounding_model(settings: Settings) -> str:
    if is_free_tier_search_grounding_model(settings.gemini_fresh_model):
        return settings.gemini_fresh_model
    return settings.gemini_search_grounding_fallback_model


def normalize_gemini_unavailable_error(error: object) -> GeminiProviderUnavailableError | None:
    status_code = _value(error, "code", "status_code")
    if isinstance(status_code, int) and status_code in {429, 503}:
        return GeminiProviderUnavailableError(status_code=status_code)
    return None


def extract_web_grounding_sources(response: object) -> list[GeminiGroundingSource]:
    metadata = _grounding_metadata(response)
    if metadata is None:
        return []
    chunks = _object_list(_value(metadata, "grounding_chunks", "groundingChunks"))
    supports = _object_list(_value(metadata, "grounding_supports", "groundingSupports"))
    supported_text_by_index = _supported_text_by_chunk_index(supports)
    labels = _web_label_by_chunk_index(chunks, supports)

    sources: list[GeminiGroundingSource] = []
    for index, chunk in enumerate(chunks):
        citation_label = labels.get(index)
        if citation_label is None:
            continue
        web = _value(chunk, "web")
        if web is None:
            continue
        uri = str(_value(web, "uri") or "")
        title = str(_value(web, "title") or uri)
        if not uri:
            continue
        evidence_text = supported_text_by_index.get(index) or title
        sources.append(
            GeminiGroundingSource(
                citation_label=citation_label,
                title=title,
                uri=uri,
                evidence_text=evidence_text,
            )
        )
    return sources


def insert_web_citation_labels(text: str, response: object) -> str:
    metadata = _grounding_metadata(response)
    if metadata is None:
        return text
    chunks = _object_list(_value(metadata, "grounding_chunks", "groundingChunks"))
    supports = _object_list(_value(metadata, "grounding_supports", "groundingSupports"))
    labels = _web_label_by_chunk_index(chunks, supports)
    ordered_supports = sorted(supports, key=_support_end_index, reverse=True)
    for support in ordered_supports:
        segment = _value(support, "segment")
        end_index = _int_value(_value(segment, "end_index", "endIndex"))
        indices = _int_list(_value(support, "grounding_chunk_indices", "groundingChunkIndices"))
        citation_labels = [labels[index] for index in indices if index in labels]
        if end_index is None or not citation_labels:
            continue
        if end_index < 0 or end_index > len(text):
            continue
        unique_labels = list(dict.fromkeys(citation_labels))
        marker = f"[{', '.join(unique_labels)}]"
        text = text[:end_index] + marker + text[end_index:]
    return text


def extract_search_suggestions_html(response: object) -> str | None:
    metadata = _grounding_metadata(response)
    if metadata is None:
        return None
    entry_point = _value(metadata, "search_entry_point", "searchEntryPoint")
    if entry_point is None:
        return None
    rendered_content = _value(entry_point, "rendered_content", "renderedContent")
    return str(rendered_content) if rendered_content else None


def _supported_text_by_chunk_index(supports: list[object]) -> dict[int, str]:
    text_by_index: dict[int, list[str]] = {}
    for support in supports:
        segment = _value(support, "segment")
        segment_text = str(_value(segment, "text") or "") if segment is not None else ""
        indices = _int_list(_value(support, "grounding_chunk_indices", "groundingChunkIndices"))
        if not segment_text:
            continue
        for index in indices:
            text_by_index.setdefault(index, []).append(segment_text)
    return {index: " ".join(parts) for index, parts in text_by_index.items()}


def _web_label_by_chunk_index(chunks: list[object], supports: list[object]) -> dict[int, str]:
    supported_indices = {
        index
        for support in supports
        for index in _int_list(_value(support, "grounding_chunk_indices", "groundingChunkIndices"))
    }
    labels: dict[int, str] = {}
    next_label = 1
    for index, chunk in enumerate(chunks):
        if index in supported_indices and _value(chunk, "web") is not None:
            labels[index] = f"web-{next_label}"
            next_label += 1
    return labels


def _support_end_index(support: object) -> int:
    return _int_value(_value(_value(support, "segment"), "end_index", "endIndex")) or 0


def _grounding_metadata(response: object) -> object | None:
    candidates = _object_list(_value(response, "candidates"))
    if not candidates:
        return None
    return _value(candidates[0], "grounding_metadata", "groundingMetadata")


def _object_list(value: object | None) -> list[object]:
    if isinstance(value, list):
        return cast(list[object], value)
    return []


def _int_list(value: object | None) -> list[int]:
    return [item for item in _object_list(value) if isinstance(item, int)]


def _int_value(value: object | None) -> int | None:
    return value if isinstance(value, int) else None


def _value(obj: object | None, *names: str) -> object | None:
    if obj is None:
        return None
    if isinstance(obj, Mapping):
        mapping = cast(Mapping[str, object], obj)
        for name in names:
            if name in mapping:
                return mapping[name]
        return None
    for name in names:
        if hasattr(obj, name):
            return cast(object | None, getattr(obj, name))
    return None


def _first_prompt_chunk_id(prompt: str) -> str | None:
    match = re.search(r"^\[([A-Za-z0-9_.:-]+)\]", prompt, flags=re.MULTILINE)
    return match.group(1) if match else None
