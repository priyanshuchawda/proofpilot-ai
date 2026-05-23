from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.evaluation.metrics import EvaluationSummary
from app.services.evaluations import EvaluationRunResponse, EvaluationService

router = APIRouter(tags=["evaluations"])


def get_evaluation_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EvaluationService:
    return EvaluationService(session)


@router.post(
    "/api/v1/evaluations/run",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_evaluation(
    service: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> EvaluationRunResponse:
    return await service.run_golden_evaluation()


@router.get(
    "/api/v1/evaluations/runs/{run_id}",
    response_model=EvaluationRunResponse,
)
async def get_evaluation_run(
    run_id: str,
    service: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> EvaluationRunResponse:
    run = await service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    return run


@router.get("/api/v1/metrics/summary", response_model=EvaluationSummary)
async def metrics_summary(
    service: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> EvaluationSummary:
    return await service.latest_summary()
