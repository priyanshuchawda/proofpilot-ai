from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import DeterministicEmbeddingProvider
from app.ai.gemini import build_gemini_provider
from app.answers.schemas import AnswerResponse
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
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
        embedding_provider=DeterministicEmbeddingProvider(),
        vector_store=QdrantVectorStore(
            url=settings.qdrant_url,
            collection="proofpilot_chunks",
        ),
        embedding_model="deterministic-local",
    )
    retrieval_service = HybridRetrievalService(
        session=session,
        embedding_service=embedding_service,
    )
    answer_service = AnswerService(
        session=session,
        gemini_provider=build_gemini_provider(settings),
        generation_model=settings.gemini_generation_model,
    )
    return QueryService(
        retrieval_service=retrieval_service,
        answer_service=answer_service,
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
