from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.documents import router as documents_router
from app.api.evaluations import router as evaluations_router
from app.api.health import router as health_router
from app.api.query import router as query_router
from app.api.settings import router as settings_router
from app.api.workspaces import router as workspaces_router


class HealthResponse(BaseModel):
    service: str
    status: str
    version: str


app = FastAPI(
    title="ProofPilot AI API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/v1/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

app.include_router(settings_router)
app.include_router(health_router)
app.include_router(workspaces_router)
app.include_router(documents_router)
app.include_router(query_router)
app.include_router(evaluations_router)


@app.get("/api/v1/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service="proofpilot-api", status="ok", version="0.1.0")
