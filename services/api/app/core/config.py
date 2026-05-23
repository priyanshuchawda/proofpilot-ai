from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), extra="ignore")

    proofpilot_env: str = "development"
    database_url: str = "postgresql+asyncpg://proofpilot:proofpilot@127.0.0.1:55432/proofpilot"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    gemini_api_key: str | None = None
    gemini_generation_model: str = "gemini-3.1-flash-lite"
    gemini_lightweight_model: str = "gemini-2.5-flash-lite"
    gemini_fresh_model: str = "gemini-3.1-flash-lite"
    gemini_search_grounding_fallback_model: str = "gemini-2.5-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-2"
    gemini_embedding_dimension: int = 768
    gemini_embeddings_enabled: bool = False
    gemini_search_grounding_enabled: bool = False
    upload_indexing_enabled: bool = True
    run_gemini_smoke: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
