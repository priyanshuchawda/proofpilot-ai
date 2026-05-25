from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.infra.health import (
    DependencyHealth,
    DependencyHealthChecker,
    get_dependency_health_checker,
)
from app.observability.telemetry import TelemetryRegistry, TelemetrySnapshot, get_telemetry_registry

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


class OperationalMetricsResponse(BaseModel):
    telemetry: TelemetrySnapshot
    dependencies: list[DependencyHealth]


@router.get("/operational", response_model=OperationalMetricsResponse)
async def operational_metrics(
    telemetry: Annotated[TelemetryRegistry, Depends(get_telemetry_registry)],
    health_checker: Annotated[DependencyHealthChecker, Depends(get_dependency_health_checker)],
) -> OperationalMetricsResponse:
    return OperationalMetricsResponse(
        telemetry=telemetry.snapshot(),
        dependencies=await health_checker(),
    )
