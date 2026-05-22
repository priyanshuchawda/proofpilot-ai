from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.infra.health import (
    DependencyHealth,
    DependencyHealthChecker,
    get_dependency_health_checker,
)

router = APIRouter(prefix="/api/v1/health", tags=["health"])


class DependencyHealthResponse(BaseModel):
    services: list[DependencyHealth]


@router.get("/dependencies", response_model=DependencyHealthResponse)
async def dependency_health(
    health_checker: Annotated[DependencyHealthChecker, Depends(get_dependency_health_checker)],
) -> DependencyHealthResponse:
    services = await health_checker()
    return DependencyHealthResponse(services=services)
