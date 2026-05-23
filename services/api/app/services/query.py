from time import perf_counter
from typing import Protocol

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.answers.contradictions import Contradiction, detect_contradictions
from app.answers.schemas import AnswerResponse
from app.cache.backends import CacheBackend
from app.cache.keys import response_cache_key
from app.cache.policy import can_cache_response
from app.db.models import LatencyMetric, QueryRun
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
        response_cache: CacheBackend | None = None,
        index_version: str = "v1",
        response_cache_ttl_seconds: int = 300,
    ) -> None:
        self._session = session
        self._retrieval_service = retrieval_service
        self._answer_service = answer_service
        self._grounding_enabled = grounding_enabled
        self._response_cache = response_cache
        self._index_version = index_version
        self._response_cache_ttl_seconds = response_cache_ttl_seconds

    async def answer_workspace_query(
        self,
        *,
        workspace_id: str,
        query: str,
        mode: str,
    ) -> AnswerResponse:
        mode_value = QueryMode(mode)
        cache_key = response_cache_key(
            workspace_id=workspace_id,
            index_version=self._index_version,
            query=query,
            mode=mode,
        )
        if self._response_cache is not None:
            cached = await self._response_cache.get_json(cache_key)
            if cached is not None:
                return AnswerResponse.model_validate(cached).model_copy(
                    update={"cache_status": "hit"}
                )

        total_started_at = perf_counter()
        retrieval_started_at = perf_counter()
        retrieval = await self._retrieval_service.retrieve(
            workspace_id=workspace_id,
            query=query,
            mode=mode,
            limit=6 if mode_value == QueryMode.VERIFIED else 3,
        )
        retrieval_ms = _elapsed_ms(retrieval_started_at)
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
        answer_started_at = perf_counter()
        answer = await self._answer_service.generate_answer(
            retrieval=retrieval,
            query=query,
            mode=mode,
            route=route_decision.route,
            freshness_label=route_decision.freshness_label,
            contradictions=contradictions,
        )
        answer_ms = _elapsed_ms(answer_started_at)
        self._record_latency(
            query_run_id=retrieval.query_run_id,
            metric_name="retrieval_ms",
            duration_ms=retrieval_ms,
        )
        self._record_latency(
            query_run_id=retrieval.query_run_id,
            metric_name="answer_ms",
            duration_ms=answer_ms,
        )
        self._record_latency(
            query_run_id=retrieval.query_run_id,
            metric_name="total_query_ms",
            duration_ms=_elapsed_ms(total_started_at),
        )
        await self._session.commit()
        if self._response_cache is not None and can_cache_response(answer):
            await self._response_cache.set_json(
                cache_key,
                answer.model_dump(mode="json"),
                ttl_seconds=self._response_cache_ttl_seconds,
            )
        return answer

    def _record_latency(
        self,
        *,
        query_run_id: str,
        metric_name: str,
        duration_ms: int,
    ) -> None:
        self._session.add(
            LatencyMetric(
                query_run_id=query_run_id,
                metric_name=metric_name,
                duration_ms=duration_ms,
            )
        )


def _elapsed_ms(started_at: float) -> int:
    return max(0, int((perf_counter() - started_at) * 1000))
