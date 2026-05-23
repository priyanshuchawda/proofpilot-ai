from collections.abc import AsyncIterator

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import (
    CitedEvidence,
    Document,
    DocumentChunk,
    DocumentVersion,
    GeneratedAnswer,
    LatencyMetric,
    QueryRun,
    RetrievalCandidate,
    VerificationResult,
    Workspace,
)
from app.db.session import get_db_session
from app.main import app


async def test_query_run_detail_returns_ordered_trace_rows() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        workspace = Workspace(name="Trace", description=None)
        session.add(workspace)
        await session.flush()
        document = Document(
            workspace_id=workspace.id,
            filename="policy.md",
            mime_type="text/markdown",
            status="ready",
        )
        session.add(document)
        await session.flush()
        version = DocumentVersion(
            document_id=document.id,
            content_hash="version-hash",
            storage_path="memory",
            version_number=1,
        )
        session.add(version)
        await session.flush()
        chunk = DocumentChunk(
            workspace_id=workspace.id,
            document_id=document.id,
            document_version_id=version.id,
            source_filename=document.filename,
            mime_type=document.mime_type,
            page_number=2,
            section_heading="Eligibility",
            chunk_order=0,
            chunk_text="ProofPilot keeps grounded evidence visible.",
            token_estimate=5,
            content_hash="chunk-hash",
            redaction_status="clean",
        )
        session.add(chunk)
        await session.flush()
        query_run = QueryRun(
            workspace_id=workspace.id,
            conversation_id=None,
            query_text="What is visible?",
            route="route_document_verified",
            mode="verified",
            cache_status="miss",
        )
        session.add(query_run)
        await session.flush()
        session.add_all(
            [
                RetrievalCandidate(
                    query_run_id=query_run.id,
                    chunk_id=chunk.id,
                    source="keyword",
                    rank=2,
                    score="0.50000000",
                ),
                RetrievalCandidate(
                    query_run_id=query_run.id,
                    chunk_id=chunk.id,
                    source="hybrid",
                    rank=1,
                    score="0.75000000",
                ),
                CitedEvidence(
                    query_run_id=query_run.id,
                    chunk_id=chunk.id,
                    citation_label="chunk-a",
                    evidence_text="ProofPilot keeps grounded evidence visible.",
                    source_kind="document",
                ),
                GeneratedAnswer(
                    query_run_id=query_run.id,
                    answer_text="Grounded evidence is visible. [chunk-a]",
                    confidence_label="high",
                    refusal_reason=None,
                    live_grounding_used=False,
                ),
                VerificationResult(
                    query_run_id=query_run.id,
                    citation_valid=True,
                    unsupported_claim_count=0,
                    contradiction_count=1,
                    details={"contradictions": ["pricing"]},
                ),
                LatencyMetric(
                    query_run_id=query_run.id,
                    metric_name="retrieval_ms",
                    duration_ms=12,
                ),
            ]
        )
        await session.commit()
        query_run_id = query_run.id

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(f"/api/v1/query-runs/{query_run_id}")
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == query_run_id
    assert payload["route"] == "route_document_verified"
    assert payload["retrieval_candidates"][0]["rank"] == 1
    assert payload["retrieval_candidates"][0]["source"] == "hybrid"
    assert payload["retrieval_candidates"][0]["source_filename"] == "policy.md"
    assert payload["cited_evidence"][0]["citation_label"] == "chunk-a"
    assert payload["generated_answer"]["confidence_label"] == "high"
    assert payload["verification_result"]["contradiction_count"] == 1
    assert payload["latency_metrics"][0]["metric_name"] == "retrieval_ms"


async def test_query_run_detail_returns_404_for_unknown_run() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/query-runs/missing")
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

    assert response.status_code == 404
