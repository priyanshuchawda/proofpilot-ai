from typing import Protocol

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.answers.contradictions import Contradiction, detect_contradictions
from app.answers.schemas import AnswerResponse
from app.db.models import QueryRun
from app.retrieval.schemas import RetrievalResult
from app.routing.query import QueryMode, determine_query_route


class RetrievalServiceProtocol(Protocol):
    async def retrieve(
        self,
        *,
        workspace_id: str,
        query: str,
        mode: str,
        limit: int,
    ) -> RetrievalResult: ...


class AnswerServiceProtocol(Protocol):
    async def generate_answer(
        self,
        *,
        retrieval: RetrievalResult,
        query: str,
        mode: str,
        route: str,
        freshness_label: str,
        contradictions: list[Contradiction],
    ) -> AnswerResponse: ...


class QueryService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        retrieval_service: RetrievalServiceProtocol,
        answer_service: AnswerServiceProtocol,
        grounding_enabled: bool = False,
    ) -> None:
        self._session = session
        self._retrieval_service = retrieval_service
        self._answer_service = answer_service
        self._grounding_enabled = grounding_enabled

    async def answer_workspace_query(
        self,
        *,
        workspace_id: str,
        query: str,
        mode: str,
    ) -> AnswerResponse:
        mode_value = QueryMode(mode)
        retrieval = await self._retrieval_service.retrieve(
            workspace_id=workspace_id,
            query=query,
            mode=mode,
            limit=6 if mode_value == QueryMode.VERIFIED else 3,
        )
        route_decision = determine_query_route(
            query=query,
            mode=mode_value,
            evidence_count=len(retrieval.evidence),
            grounding_enabled=self._grounding_enabled,
        )
        await self._session.execute(
            update(QueryRun)
            .where(QueryRun.id == retrieval.query_run_id)
            .values(route=route_decision.route)
        )
        contradictions = (
            detect_contradictions(retrieval.evidence) if mode_value == QueryMode.VERIFIED else []
        )
        return await self._answer_service.generate_answer(
            retrieval=retrieval,
            query=query,
            mode=mode,
            route=route_decision.route,
            freshness_label=route_decision.freshness_label,
            contradictions=contradictions,
        )
