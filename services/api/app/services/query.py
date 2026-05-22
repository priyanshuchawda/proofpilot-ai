from app.answers.schemas import AnswerResponse
from app.services.answers import AnswerService
from app.services.retrieval import HybridRetrievalService


class QueryService:
    def __init__(
        self,
        *,
        retrieval_service: HybridRetrievalService,
        answer_service: AnswerService,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._answer_service = answer_service

    async def answer_workspace_query(
        self,
        *,
        workspace_id: str,
        query: str,
        mode: str,
    ) -> AnswerResponse:
        retrieval = await self._retrieval_service.retrieve(
            workspace_id=workspace_id,
            query=query,
            mode=mode,
            limit=6 if mode == "verified" else 3,
        )
        return await self._answer_service.generate_answer(
            retrieval=retrieval,
            query=query,
            mode=mode,
        )
