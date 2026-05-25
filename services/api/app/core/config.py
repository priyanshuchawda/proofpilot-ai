import re
from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), extra="ignore")

    proofpilot_env: str = "development"
    proofpilot_api_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    database_url: str = "postgresql+asyncpg://proofpilot:proofpilot@127.0.0.1:55432/proofpilot"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "proofpilot_chunks"
    gemini_api_key: str | None = None
    gemini_provider_mode: str = "auto"
    gemini_generation_model: str = "gemini-3.1-flash-lite"
    gemini_lightweight_model: str = "gemini-2.5-flash-lite"
    gemini_fresh_model: str = "gemini-3.1-flash-lite"
    gemini_search_grounding_fallback_model: str = "gemini-2.5-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-2"
    gemini_embedding_dimension: int = 768
    gemini_embeddings_enabled: bool = False
    gemini_search_grounding_enabled: bool = False
    upload_indexing_enabled: bool = True
    proofpilot_rate_limiting_enabled: bool = True
    proofpilot_rate_limit_sensitive_requests: int = 20
    proofpilot_rate_limit_window_seconds: int = 60
    proofpilot_workspace_ownership_enabled: bool = False
    run_gemini_smoke: bool = False

    @field_validator("proofpilot_api_cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not origins:
            raise ValueError("At least one CORS origin must be configured.")
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                origin == "*"
                or parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CORS origins must be explicit HTTP(S) origins.")
        return value

    @field_validator(
        "proofpilot_rate_limit_sensitive_requests",
        "proofpilot_rate_limit_window_seconds",
    )
    @classmethod
    def validate_positive_integer(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Rate limit settings must be positive integers.")
        return value

    @field_validator("qdrant_collection")
    @classmethod
    def validate_qdrant_collection(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
            raise ValueError(
                "Qdrant collection must contain only letters, numbers, underscores, and hyphens."
            )
        return value

    @field_validator("gemini_provider_mode")
    @classmethod
    def validate_gemini_provider_mode(cls, value: str) -> str:
        if value not in {"auto", "google", "mock"}:
            raise ValueError("Gemini provider mode must be auto, google, or mock.")
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.proofpilot_api_cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
