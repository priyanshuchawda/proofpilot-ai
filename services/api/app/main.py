from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.documents import router as documents_router
from app.api.evaluations import router as evaluations_router
from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.query import router as query_router
from app.api.query_runs import router as query_runs_router
from app.api.settings import router as settings_router
from app.api.workspaces import router as workspaces_router
from app.core.config import Settings, get_settings
from app.observability.request_logging import RequestLogMiddleware


class HealthResponse(BaseModel):
    service: str
    status: str
    version: str


async def health() -> HealthResponse:
    return HealthResponse(service="proofpilot-api", status="ok", version="0.1.0")


def create_app(settings: Settings | None = None) -> FastAPI:
    application = FastAPI(
        title="ProofPilot AI API",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/v1/openapi.json",
    )
    active_settings = settings or get_settings()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["Retry-After", "X-Request-ID"],
    )
    application.add_middleware(RequestLogMiddleware)
    application.include_router(settings_router)
    application.include_router(health_router)
    application.include_router(workspaces_router)
    application.include_router(documents_router)
    application.include_router(query_router)
    application.include_router(query_runs_router)
    application.include_router(evaluations_router)
    application.include_router(metrics_router)
    application.add_api_route(
        "/api/v1/health", health, methods=["GET"], response_model=HealthResponse
    )

    return application


app = create_app()
