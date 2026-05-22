from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), extra="ignore")

    proofpilot_env: str = "development"
    gemini_api_key: str | None = None
    gemini_generation_model: str = "gemini-2.5-flash-lite"
    gemini_lightweight_model: str = "gemini-2.5-flash-lite"
    gemini_fresh_model: str = "gemini-2.5-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-2"
    gemini_search_grounding_enabled: bool = False
    run_gemini_smoke: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
