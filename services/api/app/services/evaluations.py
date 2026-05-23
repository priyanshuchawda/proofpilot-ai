import json
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EvaluationRun
from app.evaluation.golden import golden_case_results
from app.evaluation.metrics import EvaluationSummary, summarize_evaluation_results


class EvaluationRunResponse(BaseModel):
    run_id: str
    status: str
    summary: EvaluationSummary


class EvaluationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def run_golden_evaluation(self) -> EvaluationRunResponse:
        summary = summarize_evaluation_results(golden_case_results())
        run = EvaluationRun(status="completed", summary=summary.model_dump(mode="json"))
        self._session.add(run)
        await self._session.commit()
        response = EvaluationRunResponse(
            run_id=run.id,
            status=run.status,
            summary=summary,
        )
        write_evaluation_result(response)
        return response

    async def get_run(self, run_id: str) -> EvaluationRunResponse | None:
        run = await self._session.get(EvaluationRun, run_id)
        if run is None:
            return None
        return EvaluationRunResponse(
            run_id=run.id,
            status=run.status,
            summary=EvaluationSummary.model_validate(run.summary),
        )

    async def latest_summary(self) -> EvaluationSummary:
        run = (
            (
                await self._session.execute(
                    select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(1)
                )
            )
            .scalars()
            .first()
        )
        if run is None:
            return summarize_evaluation_results([])
        return EvaluationSummary.model_validate(run.summary)


def get_evals_results_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "evals" / "results"


def write_evaluation_result(response: EvaluationRunResponse) -> None:
    results_dir = get_evals_results_dir()
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / f"{response.run_id}.json").write_text(
        json.dumps(response.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
