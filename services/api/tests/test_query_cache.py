from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.answers.schemas import AnswerResponse
from app.cache.backends import InMemoryCacheBackend
from app.cache.keys import response_cache_key
from app.db.base import Base
from app.db.models import LatencyMetric
from app.retrieval.schemas import EvidenceChunk
from app.services.query import QueryService
from tests.test_query_service import FakeAnswerService, FakeRetrievalService


def _cached_answer() -> AnswerResponse:
    return AnswerResponse(
        query_run_id="cached-run",
        answer_text="Cached answer [chunk-a]",
        citations=[],
        evidence_chunk_ids=["chunk-a"],
        confidence_label="medium",
        refusal_reason=None,
        mode="fast",
        route="route_document_fast",
        freshness_label="not_required",
        contradictions=[],
        cache_status="miss",
    )


def evidence(chunk_id: str) -> EvidenceChunk:
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


async def test_query_service_returns_workspace_scoped_response_cache_hit() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    cache = InMemoryCacheBackend()
    await cache.set_json(
        response_cache_key(
            workspace_id="workspace-a",
            index_version="v1",
            query="What is the policy?",
            mode="fast",
        ),
        _cached_answer().model_dump(mode="json"),
        ttl_seconds=60,
    )

    async with session_factory() as session:
        retrieval = FakeRetrievalService([evidence("chunk-a")])
        service = QueryService(
            session=session,
            retrieval_service=retrieval,
            answer_service=FakeAnswerService(),
            response_cache=cache,
            index_version="v1",
        )

        answer = await service.answer_workspace_query(
            workspace_id="workspace-a",
            query="What is the policy?",
            mode="fast",
        )

    await engine.dispose()

    assert answer.cache_status == "hit"
    assert answer.answer_text == "Cached answer [chunk-a]"
    assert retrieval.calls == []


async def test_query_service_stores_safe_response_cache_miss() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    cache = InMemoryCacheBackend()

    async with session_factory() as session:
        service = QueryService(
            session=session,
            retrieval_service=FakeRetrievalService([evidence("chunk-a")]),
            answer_service=FakeAnswerService(),
            response_cache=cache,
            index_version="v1",
        )

        answer = await service.answer_workspace_query(
            workspace_id="workspace-a",
            query="What is the policy?",
            mode="fast",
        )

    await engine.dispose()

    assert answer.cache_status == "miss"
    assert len(cache.values) == 1


async def test_query_service_records_latency_metrics_without_document_content() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        service = QueryService(
            session=session,
            retrieval_service=FakeRetrievalService([evidence("chunk-a")]),
            answer_service=FakeAnswerService(),
            response_cache=InMemoryCacheBackend(),
            index_version="v1",
        )

        await service.answer_workspace_query(
            workspace_id="workspace-a",
            query="What is the policy?",
            mode="fast",
        )

        metrics = (await session.execute(select(LatencyMetric))).scalars().all()

    await engine.dispose()

    assert {metric.metric_name for metric in metrics} >= {
        "retrieval_ms",
        "answer_ms",
        "total_query_ms",
    }
    assert all("policy" not in metric.metric_name.lower() for metric in metrics)
