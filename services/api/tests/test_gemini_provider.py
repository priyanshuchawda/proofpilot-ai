from types import SimpleNamespace

import pytest

from app.ai.gemini import (
    GeminiGenerateRequest,
    GeminiProviderUnavailableError,
    GoogleGenAIProvider,
    MissingGeminiApiKeyError,
    MockGeminiProvider,
    build_gemini_provider,
    choose_search_grounding_model,
    extract_search_suggestions_html,
    extract_web_grounding_sources,
    insert_web_citation_labels,
    is_free_tier_search_grounding_model,
    normalize_gemini_unavailable_error,
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


def test_search_grounding_model_guard_rejects_gemini_3_flash_lite_free_tier() -> None:
    assert not is_free_tier_search_grounding_model("gemini-3.1-flash-lite")
    assert not is_free_tier_search_grounding_model("gemini-3.1-flash-lite-preview")
    assert is_free_tier_search_grounding_model("gemini-2.5-flash-lite")


def test_search_grounding_model_falls_back_to_free_tier_safe_model() -> None:
    settings = Settings(
        gemini_fresh_model="gemini-3.1-flash-lite",
        gemini_search_grounding_fallback_model="gemini-2.5-flash-lite",
    )

    selected = choose_search_grounding_model(settings)

    assert selected == "gemini-2.5-flash-lite"


def test_extract_web_grounding_sources_from_google_response_metadata() -> None:
    response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                grounding_metadata=SimpleNamespace(
                    grounding_chunks=[
                        SimpleNamespace(
                            web=SimpleNamespace(
                                title="Gemini API models",
                                uri="https://ai.google.dev/gemini-api/docs/models",
                            )
                        )
                    ],
                    grounding_supports=[
                        SimpleNamespace(
                            segment=SimpleNamespace(
                                text="Gemini API models include current Flash models."
                            ),
                            grounding_chunk_indices=[0],
                        )
                    ],
                )
            )
        ]
    )

    sources = extract_web_grounding_sources(response)

    assert len(sources) == 1
    assert sources[0].citation_label == "web-1"
    assert sources[0].title == "Gemini API models"
    assert sources[0].uri == "https://ai.google.dev/gemini-api/docs/models"
    assert sources[0].evidence_text == "Gemini API models include current Flash models."


def test_grounding_omits_unreferenced_web_chunks_and_keeps_inline_labels_aligned() -> None:
    response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                grounding_metadata=SimpleNamespace(
                    grounding_chunks=[
                        SimpleNamespace(
                            web=SimpleNamespace(
                                title="Unused result",
                                uri="https://example.test/unused",
                            )
                        ),
                        SimpleNamespace(
                            web=SimpleNamespace(
                                title="Cited result",
                                uri="https://example.test/cited",
                            )
                        ),
                    ],
                    grounding_supports=[
                        SimpleNamespace(
                            segment=SimpleNamespace(
                                text="Current facts.",
                                end_index=14,
                            ),
                            grounding_chunk_indices=[1],
                        )
                    ],
                )
            )
        ]
    )

    sources = extract_web_grounding_sources(response)
    text = insert_web_citation_labels("Current facts.", response)

    assert [source.uri for source in sources] == ["https://example.test/cited"]
    assert sources[0].citation_label == "web-1"
    assert text == "Current facts.[web-1]"


def test_insert_web_citation_labels_from_grounding_support_ranges() -> None:
    response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                grounding_metadata=SimpleNamespace(
                    grounding_chunks=[
                        SimpleNamespace(web=SimpleNamespace(uri="https://source.example/one")),
                        SimpleNamespace(web=SimpleNamespace(uri="https://source.example/two")),
                    ],
                    grounding_supports=[
                        SimpleNamespace(
                            segment=SimpleNamespace(end_index=14),
                            grounding_chunk_indices=[0, 1],
                        )
                    ],
                )
            )
        ]
    )

    text = insert_web_citation_labels("Current facts.", response)

    assert text == "Current facts.[web-1, web-2]"


def test_extract_search_suggestions_html_from_grounding_metadata() -> None:
    response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                grounding_metadata=SimpleNamespace(
                    search_entry_point=SimpleNamespace(
                        rendered_content='<div class="search-chip">Google Search</div>'
                    )
                )
            )
        ]
    )

    html = extract_search_suggestions_html(response)

    assert html == '<div class="search-chip">Google Search</div>'


def test_normalize_gemini_unavailable_error_maps_quota_and_service_overload() -> None:
    quota_error = normalize_gemini_unavailable_error(SimpleNamespace(code=429))
    overload_error = normalize_gemini_unavailable_error(SimpleNamespace(code=503))
    unrelated_error = normalize_gemini_unavailable_error(SimpleNamespace(code=400))

    assert isinstance(quota_error, GeminiProviderUnavailableError)
    assert quota_error.status_code == 429
    assert isinstance(overload_error, GeminiProviderUnavailableError)
    assert overload_error.status_code == 503
    assert unrelated_error is None
