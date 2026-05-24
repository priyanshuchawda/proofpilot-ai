import json
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import build_embedding_provider
from app.ai.gemini import build_gemini_provider, choose_search_grounding_model
from app.answers.schemas import AnswerResponse
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.retrieval.keyword import PostgresKeywordRetriever
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
) -> QueryService:
    embedding_service = EmbeddingIndexService(
        session=session,
        embedding_provider=build_embedding_provider(settings),
        vector_store=QdrantVectorStore(
            url=settings.qdrant_url,
            collection="proofpilot_chunks",
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
        gemini_provider=build_gemini_provider(settings),
        generation_model=settings.gemini_generation_model,
        fallback_generation_model=settings.gemini_lightweight_model,
        grounding_model=choose_search_grounding_model(settings),
    )
    return QueryService(
        session=session,
        retrieval_service=retrieval_service,
        answer_service=answer_service,
        grounding_enabled=settings.gemini_search_grounding_enabled,
    )


@router.post(
    "/api/v1/workspaces/{workspace_id}/query",
    response_model=AnswerResponse,
)
async def query_workspace(
    workspace_id: str,
    request: QueryRequest,
    service: Annotated[QueryService, Depends(get_query_service)],
) -> AnswerResponse:
    return await service.answer_workspace_query(
        workspace_id=workspace_id,
        query=request.query,
        mode=request.mode,
    )


@router.post("/api/v1/workspaces/{workspace_id}/query/stream")
async def query_workspace_stream(
    workspace_id: str,
    request: QueryRequest,
    service: Annotated[QueryService, Depends(get_query_service)],
) -> StreamingResponse:
    answer = await service.answer_workspace_query(
        workspace_id=workspace_id,
        query=request.query,
        mode=request.mode,
    )

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
