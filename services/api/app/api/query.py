import json
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import build_embedding_provider
from app.ai.gemini import (
    InstrumentedGeminiProvider,
    build_gemini_provider,
    choose_search_grounding_model,
)
from app.answers.schemas import AnswerResponse
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.observability.telemetry import TelemetryRegistry, get_telemetry_registry
from app.retrieval.keyword import PostgresKeywordRetriever
from app.security.local_session import LocalSession, ensure_workspace_owner, get_local_session
from app.security.rate_limiting import enforce_sensitive_rate_limit
from app.services.answers import AnswerService
from app.services.embedding_index import EmbeddingIndexService
from app.services.query import QueryService
from app.services.retrieval import HybridRetrievalService
from app.vector.qdrant import QdrantVectorStore

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    mode: Literal["fast", "verified"] = "fast"


def get_query_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    telemetry: Annotated[TelemetryRegistry, Depends(get_telemetry_registry)],
) -> QueryService:
    embedding_service = EmbeddingIndexService(
        session=session,
        embedding_provider=build_embedding_provider(settings),
        vector_store=QdrantVectorStore(
            url=settings.qdrant_url,
            collection=settings.qdrant_collection,
        ),
        embedding_model=(
            settings.gemini_embedding_model
            if settings.gemini_embeddings_enabled
            else "deterministic-local"
        ),
    )
    retrieval_service = HybridRetrievalService(
        session=session,
        embedding_service=embedding_service,
        keyword_retriever=PostgresKeywordRetriever(session=session),
    )
    answer_service = AnswerService(
        session=session,
        gemini_provider=InstrumentedGeminiProvider(
            provider=build_gemini_provider(settings),
            telemetry=telemetry,
        ),
        generation_model=settings.gemini_generation_model,
        fallback_generation_model=settings.gemini_lightweight_model,
        grounding_model=choose_search_grounding_model(settings),
    )
    return QueryService(
        session=session,
        retrieval_service=retrieval_service,
        answer_service=answer_service,
        grounding_enabled=settings.gemini_search_grounding_enabled,
        telemetry=telemetry,
    )


@router.post(
    "/api/v1/workspaces/{workspace_id}/query",
    response_model=AnswerResponse,
)
async def query_workspace(
    workspace_id: str,
    http_request: Request,
    request: QueryRequest,
    _rate_limit: Annotated[None, Depends(enforce_sensitive_rate_limit)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    local_session: Annotated[LocalSession, Depends(get_local_session)],
    service: Annotated[QueryService, Depends(get_query_service)],
) -> AnswerResponse:
    del _rate_limit
    await ensure_workspace_owner(
        workspace_id=workspace_id,
        session=db_session,
        local_session=local_session,
        settings=settings,
    )
    answer = await service.answer_workspace_query(
        workspace_id=workspace_id,
        query=request.query,
        mode=request.mode,
    )
    _attach_answer_telemetry(http_request, answer)
    return answer


@router.post("/api/v1/workspaces/{workspace_id}/query/stream")
async def query_workspace_stream(
    workspace_id: str,
    http_request: Request,
    request: QueryRequest,
    _rate_limit: Annotated[None, Depends(enforce_sensitive_rate_limit)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    local_session: Annotated[LocalSession, Depends(get_local_session)],
    service: Annotated[QueryService, Depends(get_query_service)],
) -> StreamingResponse:
    del _rate_limit
    await ensure_workspace_owner(
        workspace_id=workspace_id,
        session=db_session,
        local_session=local_session,
        settings=settings,
    )
    answer = await service.answer_workspace_query(
        workspace_id=workspace_id,
        query=request.query,
        mode=request.mode,
    )
    _attach_answer_telemetry(http_request, answer)

    async def events() -> AsyncIterator[str]:
        visible_text = answer.refusal_reason or answer.answer_text
        for delta in _answer_deltas(visible_text):
            yield _sse_event("answer_delta", {"text": delta})
        yield _sse_event("final", json.loads(answer.model_dump_json()))

    return StreamingResponse(events(), media_type="text/event-stream")


def _answer_deltas(text: str) -> list[str]:
    words = text.split(" ")
    return [f"{word} " if index < len(words) - 1 else word for index, word in enumerate(words)]


def _sse_event(event: str, payload: object) -> str:
    data = json.dumps(payload, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n"


def _attach_answer_telemetry(request: Request, answer: AnswerResponse) -> None:
    request.state.query_run_id = answer.query_run_id
    request.state.cache_status = answer.cache_status
    request.state.generation_model_used = answer.generation_model_used
    request.state.live_grounding_used = answer.live_grounding_used
