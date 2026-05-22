from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class AISettingsResponse(BaseModel):
    backend_only: bool
    gemini_configured: bool
    generation_model: str
    lightweight_model: str
    freshness_model: str
    embedding_model: str
    search_grounding_enabled: bool
    live_smoke_enabled: bool


@router.get("/ai", response_model=AISettingsResponse)
async def get_ai_settings(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AISettingsResponse:
    return AISettingsResponse(
        backend_only=True,
        gemini_configured=bool(settings.gemini_api_key),
        generation_model=settings.gemini_generation_model,
        lightweight_model=settings.gemini_lightweight_model,
        freshness_model=settings.gemini_fresh_model,
        embedding_model=settings.gemini_embedding_model,
        search_grounding_enabled=settings.gemini_search_grounding_enabled,
        live_smoke_enabled=settings.run_gemini_smoke,
    )
