from hashlib import sha256
from threading import Lock

from pydantic import BaseModel


class GeminiRequestMetric(BaseModel):
    provider: str
    model: str
    google_search: bool
    count: int


class GeminiErrorMetric(BaseModel):
    provider: str
    model: str
    status_code: int | None
    count: int


class CacheEventMetric(BaseModel):
    cache_name: str
    result: str
    workspace_hash: str
    mode: str
    count: int


class TelemetrySnapshot(BaseModel):
    gemini_requests: list[GeminiRequestMetric]
    gemini_errors: list[GeminiErrorMetric]
    cache_events: list[CacheEventMetric]


class TelemetryRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._gemini_requests: dict[tuple[str, str, bool], int] = {}
        self._gemini_errors: dict[tuple[str, str, int | None], int] = {}
        self._cache_events: dict[tuple[str, str, str, str], int] = {}

    def record_gemini_request(
        self,
        *,
        provider: str,
        model: str,
        google_search: bool,
    ) -> None:
        key = (provider, model, google_search)
        with self._lock:
            self._gemini_requests[key] = self._gemini_requests.get(key, 0) + 1

    def record_gemini_error(
        self,
        *,
        provider: str,
        model: str,
        status_code: int | None,
    ) -> None:
        key = (provider, model, status_code)
        with self._lock:
            self._gemini_errors[key] = self._gemini_errors.get(key, 0) + 1

    def record_cache_event(
        self,
        *,
        cache_name: str,
        result: str,
        workspace_id: str,
        mode: str,
    ) -> None:
        key = (cache_name, result, _workspace_hash(workspace_id), mode)
        with self._lock:
            self._cache_events[key] = self._cache_events.get(key, 0) + 1

    def snapshot(self) -> TelemetrySnapshot:
        with self._lock:
            gemini_requests = [
                GeminiRequestMetric(
                    provider=provider,
                    model=model,
                    google_search=google_search,
                    count=count,
                )
                for (provider, model, google_search), count in self._gemini_requests.items()
            ]
            gemini_errors = [
                GeminiErrorMetric(
                    provider=provider,
                    model=model,
                    status_code=status_code,
                    count=count,
                )
                for (provider, model, status_code), count in self._gemini_errors.items()
            ]
            cache_events = [
                CacheEventMetric(
                    cache_name=cache_name,
                    result=result,
                    workspace_hash=workspace_hash,
                    mode=mode,
                    count=count,
                )
                for (
                    cache_name,
                    result,
                    workspace_hash,
                    mode,
                ), count in self._cache_events.items()
            ]
        return TelemetrySnapshot(
            gemini_requests=gemini_requests,
            gemini_errors=gemini_errors,
            cache_events=cache_events,
        )


_telemetry_registry = TelemetryRegistry()


def get_telemetry_registry() -> TelemetryRegistry:
    return _telemetry_registry


def _workspace_hash(workspace_id: str) -> str:
    return sha256(workspace_id.encode("utf-8")).hexdigest()[:16]
