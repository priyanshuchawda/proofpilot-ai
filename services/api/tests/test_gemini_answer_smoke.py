import os

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.gemini import GoogleGenAIProvider
from app.core.config import get_settings
from app.db.base import Base
from app.db.models import QueryRun
from app.retrieval.schemas import EvidenceChunk, RetrievalResult
from app.services.answers import AnswerService


@pytest.mark.skipif(
    os.getenv("RUN_GEMINI_ANSWER_SMOKE") != "1",
    reason="Real Gemini cited-answer smoke tests are opt-in only.",
)
async def test_real_gemini_flash_lite_cited_answer_smoke() -> None:
    settings = get_settings()
    if not settings.gemini_api_key:
        pytest.skip("GEMINI_API_KEY is required for the opt-in cited-answer smoke.")

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        query_run = QueryRun(
            workspace_id="workspace-smoke",
            conversation_id=None,
            query_text="What does the public smoke note require?",
            route="route_document_verified",
            mode="verified",
            cache_status="miss",
        )
        session.add(query_run)
        await session.commit()

        service = AnswerService(
            session=session,
            gemini_provider=GoogleGenAIProvider(api_key=settings.gemini_api_key),
            generation_model="gemini-2.5-flash-lite",
            fallback_generation_model="gemini-2.5-flash-lite",
        )

        answer = await service.generate_answer(
            retrieval=RetrievalResult(
                query_run_id=query_run.id,
                evidence=[
                    EvidenceChunk(
                        chunk_id="chunk-a",
                        workspace_id="workspace-smoke",
                        document_id="document-smoke",
                        document_version_id="version-smoke",
                        source_filename="public-smoke.md",
                        mime_type="text/markdown",
                        page_number=None,
                        section_heading="Smoke",
                        chunk_order=0,
                        text=(
                            "The public smoke note requires citation-checked answers for "
                            "ProofPilot verification."
                        ),
                        score=0.99,
                        source="hybrid",
                    )
                ],
            ),
            query="What does the public smoke note require?",
            mode="verified",
            route="route_document_verified",
            freshness_label="not_required",
            contradictions=[],
        )

    await engine.dispose()

    assert answer.refusal_reason is None
    assert answer.generation_model_used == "gemini-2.5-flash-lite"
    assert answer.evidence_chunk_ids == ["chunk-a"]
    assert [citation.chunk_id for citation in answer.citations] == ["chunk-a"]
    assert "citation" in answer.answer_text.lower()
