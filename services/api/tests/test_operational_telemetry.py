import json
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.ai.gemini import (
    GeminiGenerateRequest,
    GeminiGenerateResponse,
    GeminiProviderUnavailableError,
    InstrumentedGeminiProvider,
)
from app.cache.backends import InMemoryCacheBackend
from app.cache.keys import response_cache_key
from app.db.base import Base
from app.db.session import get_db_session
from app.infra.health import DependencyHealth, get_dependency_health_checker
from app.main import app
from app.observability.telemetry import TelemetryRegistry, get_telemetry_registry
from app.retrieval.schemas import EvidenceChunk
from app.services.query import QueryService
from tests.test_query_service import FakeAnswerService, FakeRetrievalService


class SuccessfulProvider:
    async def generate_text(self, request: GeminiGenerateRequest) -> GeminiGenerateResponse:
        return GeminiGenerateResponse(
            text="ok",
            model=request.model,
            provider="fake-google",
        )


class FailingProvider:
    async def generate_text(self, request: GeminiGenerateRequest) -> GeminiGenerateResponse:
        raise GeminiProviderUnavailableError(status_code=429)


async def test_instrumented_gemini_provider_records_safe_counts_without_prompt_or_key() -> None:
    telemetry = TelemetryRegistry()
    provider = InstrumentedGeminiProvider(
        provider=SuccessfulProvider(),
        telemetry=telemetry,
    )

    await provider.generate_text(
        GeminiGenerateRequest(
            prompt="Summarize this fake secret: AIzaSySecretShouldNotAppear",
            model="gemini-2.5-flash-lite",
            enable_google_search=True,
        )
    )

    snapshot = telemetry.snapshot()
    serialized = json.dumps(snapshot.model_dump(mode="json"))

    assert snapshot.gemini_requests[0].count == 1
    assert snapshot.gemini_requests[0].model == "gemini-2.5-flash-lite"
    assert snapshot.gemini_requests[0].provider == "fake-google"
    assert snapshot.gemini_requests[0].google_search is True
    assert "Summarize" not in serialized
    assert "AIzaSySecretShouldNotAppear" not in serialized


async def test_instrumented_gemini_provider_records_safe_error_counts() -> None:
    telemetry = TelemetryRegistry()
    provider = InstrumentedGeminiProvider(
        provider=FailingProvider(),
        telemetry=telemetry,
    )

    with pytest.raises(GeminiProviderUnavailableError):
        await provider.generate_text(
            GeminiGenerateRequest(
                prompt="Do not log this prompt",
                model="gemini-2.5-flash-lite",
            )
        )

    snapshot = telemetry.snapshot()

    assert snapshot.gemini_errors[0].count == 1
    assert snapshot.gemini_errors[0].model == "gemini-2.5-flash-lite"
    assert snapshot.gemini_errors[0].provider == "unknown"
    assert snapshot.gemini_errors[0].status_code == 429


def _evidence(chunk_id: str) -> EvidenceChunk:
    return EvidenceChunk(
        chunk_id=chunk_id,
        workspace_id="workspace-a",
        document_id="document-a",
        document_version_id="version-a",
        source_filename="policy.md",
        mime_type="text/markdown",
        page_number=None,
        section_heading="Policy",
        chunk_order=0,
        text="Evidence text.",
        score=0.9,
        source="hybrid",
    )


async def test_query_service_records_workspace_scoped_cache_metrics_without_raw_workspace() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    cache = InMemoryCacheBackend()
    telemetry = TelemetryRegistry()
    await cache.set_json(
        response_cache_key(
            workspace_id="workspace-a",
            index_version="v1",
            query="What is the policy?",
            mode="fast",
        ),
        {
            "query_run_id": "cached-run",
            "answer_text": "Cached answer [chunk-a]",
            "citations": [],
            "evidence_chunk_ids": ["chunk-a"],
            "confidence_label": "medium",
            "refusal_reason": None,
            "mode": "fast",
            "route": "route_document_fast",
            "freshness_label": "not_required",
            "contradictions": [],
            "cache_status": "miss",
        },
        ttl_seconds=60,
    )

    async with session_factory() as session:
        service = QueryService(
            session=session,
            retrieval_service=FakeRetrievalService([_evidence("chunk-a")]),
            answer_service=FakeAnswerService(),
            response_cache=cache,
            index_version="v1",
            telemetry=telemetry,
        )
        await service.answer_workspace_query(
            workspace_id="workspace-a",
            query="What is the policy?",
            mode="fast",
        )
        await service.answer_workspace_query(
            workspace_id="workspace-b",
            query="What is the policy?",
            mode="fast",
        )

    await engine.dispose()
    snapshot = telemetry.snapshot()
    serialized = json.dumps(snapshot.model_dump(mode="json"))

    assert [entry.result for entry in snapshot.cache_events] == ["hit", "miss"]
    assert all(entry.workspace_hash for entry in snapshot.cache_events)
    assert "workspace-a" not in serialized
    assert "workspace-b" not in serialized
    assert "What is the policy?" not in serialized


async def test_operational_metrics_endpoint_returns_safe_dependency_snapshot() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    telemetry = TelemetryRegistry()

    async def test_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    async def fake_health_checker() -> list[DependencyHealth]:
        return [
            DependencyHealth(name="postgres", status="ok"),
            DependencyHealth(name="redis", status="error", detail="ConnectionError"),
        ]

    app.dependency_overrides[get_db_session] = test_session
    app.dependency_overrides[get_dependency_health_checker] = lambda: fake_health_checker
    app.dependency_overrides[get_telemetry_registry] = lambda: telemetry
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/metrics/operational")
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

    assert response.status_code == 200
    assert response.json()["dependencies"] == [
        {"name": "postgres", "status": "ok", "detail": None},
        {"name": "redis", "status": "error", "detail": "ConnectionError"},
    ]
