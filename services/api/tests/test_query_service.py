from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.answers.contradictions import Contradiction
from app.answers.schemas import AnswerResponse
from app.db.base import Base
from app.retrieval.schemas import EvidenceChunk, RetrievalResult
from app.services.query import QueryService


class FakeRetrievalService:
    def __init__(self, evidence: list[EvidenceChunk]) -> None:
        self.evidence = evidence
        self.calls: list[dict[str, object]] = []

    async def retrieve(
        self,
        *,
        workspace_id: str,
        query: str,
        mode: str,
        limit: int,
    ) -> RetrievalResult:
        self.calls.append(
            {"workspace_id": workspace_id, "query": query, "mode": mode, "limit": limit}
        )
        return RetrievalResult(query_run_id="query-run-a", evidence=self.evidence)


class FakeAnswerService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def generate_answer(
        self,
        *,
        retrieval: RetrievalResult,
        query: str,
        mode: str,
        route: str,
        freshness_label: str,
        contradictions: list[Contradiction],
    ) -> AnswerResponse:
        self.calls.append(
            {
                "retrieval": retrieval,
                "query": query,
                "mode": mode,
                "route": route,
                "freshness_label": freshness_label,
                "contradictions": contradictions,
            }
        )
        return AnswerResponse(
            query_run_id=retrieval.query_run_id,
            answer_text="answer",
            citations=[],
            evidence_chunk_ids=[item.chunk_id for item in retrieval.evidence],
            confidence_label="medium",
            refusal_reason=None,
            mode=mode,
            route=route,
            freshness_label=freshness_label,
            contradictions=contradictions,
        )


def _evidence(chunk_id: str, text: str = "Evidence text.") -> EvidenceChunk:
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
        text=text,
        score=0.9,
        source="hybrid",
    )


async def test_query_service_uses_fast_and_verified_candidate_limits() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        retrieval = FakeRetrievalService([_evidence("chunk-a")])
        service = QueryService(
            session=session,
            retrieval_service=retrieval,
            answer_service=FakeAnswerService(),
        )

        await service.answer_workspace_query(
            workspace_id="workspace-a",
            query="Summarize",
            mode="fast",
        )
        await service.answer_workspace_query(
            workspace_id="workspace-a",
            query="Summarize",
            mode="verified",
        )

    await engine.dispose()

    assert retrieval.calls[0]["limit"] == 3
    assert retrieval.calls[1]["limit"] == 6


async def test_query_service_adds_route_freshness_and_contradictions() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        answer_service = FakeAnswerService()
        service = QueryService(
            session=session,
            retrieval_service=FakeRetrievalService(
                [
                    _evidence("chunk-a", "The retention period is 30 days."),
                    _evidence("chunk-b", "The retention period is 90 days."),
                ]
            ),
            answer_service=answer_service,
            grounding_enabled=False,
        )

        answer = await service.answer_workspace_query(
            workspace_id="workspace-a",
            query="What is the latest retention period?",
            mode="verified",
        )

    await engine.dispose()

    assert answer.route == "route_freshness_required"
    assert answer.freshness_label == "freshness_required_grounding_disabled"
    assert len(answer.contradictions) == 1
    assert answer.contradictions[0].claim_key == "retention period"
