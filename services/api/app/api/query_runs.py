from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models import (
    CitedEvidence,
    DocumentChunk,
    GeneratedAnswer,
    LatencyMetric,
    QueryRun,
    RetrievalCandidate,
    VerificationResult,
)
from app.db.session import get_db_session
from app.security.local_session import LocalSession, ensure_workspace_owner, get_local_session

router = APIRouter(tags=["query-runs"])


class RetrievalCandidateTrace(BaseModel):
    chunk_id: str
    source: str
    rank: int
    score: str
    source_filename: str | None = None
    page_number: int | None = None
    section_heading: str | None = None


class CitedEvidenceTrace(BaseModel):
    chunk_id: str | None
    citation_label: str
    evidence_text: str
    source_kind: str


class GeneratedAnswerTrace(BaseModel):
    answer_text: str
    confidence_label: str
    refusal_reason: str | None
    live_grounding_used: bool


class VerificationResultTrace(BaseModel):
    citation_valid: bool
    unsupported_claim_count: int
    contradiction_count: int
    details: dict[str, object]


class LatencyMetricTrace(BaseModel):
    metric_name: str
    duration_ms: int


class QueryRunTraceResponse(BaseModel):
    id: str
    workspace_id: str
    query_text: str
    route: str
    mode: str
    cache_status: str
    retrieval_candidates: list[RetrievalCandidateTrace]
    cited_evidence: list[CitedEvidenceTrace]
    generated_answer: GeneratedAnswerTrace | None
    verification_result: VerificationResultTrace | None
    latency_metrics: list[LatencyMetricTrace]


@router.get("/api/v1/query-runs/{query_run_id}", response_model=QueryRunTraceResponse)
async def get_query_run_trace(
    query_run_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    local_session: Annotated[LocalSession, Depends(get_local_session)],
) -> QueryRunTraceResponse:
    query_run = await session.get(QueryRun, query_run_id)
    if query_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query run not found.",
        )
    await ensure_workspace_owner(
        workspace_id=query_run.workspace_id,
        session=session,
        local_session=local_session,
        settings=settings,
    )

    candidates = (
        await session.execute(
            select(RetrievalCandidate, DocumentChunk)
            .join(DocumentChunk, RetrievalCandidate.chunk_id == DocumentChunk.id, isouter=True)
            .where(RetrievalCandidate.query_run_id == query_run_id)
            .order_by(RetrievalCandidate.rank, RetrievalCandidate.id)
        )
    ).all()
    cited_evidence = (
        (
            await session.execute(
                select(CitedEvidence)
                .where(CitedEvidence.query_run_id == query_run_id)
                .order_by(CitedEvidence.citation_label, CitedEvidence.id)
            )
        )
        .scalars()
        .all()
    )
    generated_answer = (
        (
            await session.execute(
                select(GeneratedAnswer)
                .where(GeneratedAnswer.query_run_id == query_run_id)
                .order_by(GeneratedAnswer.created_at.desc(), GeneratedAnswer.id)
            )
        )
        .scalars()
        .first()
    )
    verification_result = (
        (
            await session.execute(
                select(VerificationResult)
                .where(VerificationResult.query_run_id == query_run_id)
                .order_by(VerificationResult.created_at.desc(), VerificationResult.id)
            )
        )
        .scalars()
        .first()
    )
    latency_metrics = (
        (
            await session.execute(
                select(LatencyMetric)
                .where(LatencyMetric.query_run_id == query_run_id)
                .order_by(LatencyMetric.metric_name, LatencyMetric.id)
            )
        )
        .scalars()
        .all()
    )

    return QueryRunTraceResponse(
        id=query_run.id,
        workspace_id=query_run.workspace_id,
        query_text=query_run.query_text,
        route=query_run.route,
        mode=query_run.mode,
        cache_status=query_run.cache_status,
        retrieval_candidates=[
            RetrievalCandidateTrace(
                chunk_id=candidate.chunk_id,
                source=candidate.source,
                rank=candidate.rank,
                score=candidate.score,
                source_filename=chunk.source_filename if chunk else None,
                page_number=chunk.page_number if chunk else None,
                section_heading=chunk.section_heading if chunk else None,
            )
            for candidate, chunk in candidates
        ],
        cited_evidence=[
            CitedEvidenceTrace(
                chunk_id=evidence.chunk_id,
                citation_label=evidence.citation_label,
                evidence_text=evidence.evidence_text,
                source_kind=evidence.source_kind,
            )
            for evidence in cited_evidence
        ],
        generated_answer=GeneratedAnswerTrace(
            answer_text=generated_answer.answer_text,
            confidence_label=generated_answer.confidence_label,
            refusal_reason=generated_answer.refusal_reason,
            live_grounding_used=generated_answer.live_grounding_used,
        )
        if generated_answer
        else None,
        verification_result=VerificationResultTrace(
            citation_valid=verification_result.citation_valid,
            unsupported_claim_count=verification_result.unsupported_claim_count,
            contradiction_count=verification_result.contradiction_count,
            details=verification_result.details,
        )
        if verification_result
        else None,
        latency_metrics=[
            LatencyMetricTrace(metric_name=metric.metric_name, duration_ms=metric.duration_ms)
            for metric in latency_metrics
        ],
    )
