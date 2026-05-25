import json
import logging
from collections.abc import AsyncIterator
from typing import Any, cast

from httpx import ASGITransport, AsyncClient
from pytest import LogCaptureFixture

from app.answers.schemas import AnswerResponse
from app.api.query import get_query_service
from app.core.config import Settings, get_settings
from app.main import app
from app.security.rate_limiting import RateLimiter, RateLimitExceededError, get_rate_limiter


async def test_request_logging_emits_trace_safe_json_and_request_id(
    caplog: LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="proofpilot.request")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/v1/health?api_key=AIzaSyD-example-secret-value-123456789",
            headers={"X-Request-ID": "request-test-1"},
        )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "request-test-1"

    messages = _request_log_messages(caplog)
    assert len(messages) == 1
    payload = cast(dict[str, Any], json.loads(messages[0]))
    assert payload["event"] == "http_request"
    assert payload["request_id"] == "request-test-1"
    assert payload["method"] == "GET"
    assert payload["path"] == "/api/v1/health"
    assert payload["status_code"] == 200
    assert isinstance(payload["duration_ms"], int)
    assert "api_key" not in messages[0]
    assert "AIzaSyD-example-secret-value" not in messages[0]


async def test_request_logging_generates_request_id_when_missing(
    caplog: LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="proofpilot.request")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/health")

    request_id = response.headers["x-request-id"]
    assert request_id
    payload = cast(dict[str, Any], json.loads(_request_log_messages(caplog)[0]))
    assert payload["request_id"] == request_id


async def test_request_logging_marks_rate_limited_requests_without_body_leakage(
    caplog: LogCaptureFixture,
) -> None:
    class ExhaustedLimiter:
        async def enforce(
            self,
            *,
            bucket: str,
            client_identifier: str,
            limit: int,
            window_seconds: int,
        ) -> None:
            del bucket, client_identifier, limit, window_seconds
            raise RateLimitExceededError(retry_after_seconds=12)

    async def override_limiter() -> AsyncIterator[RateLimiter]:
        yield ExhaustedLimiter()

    caplog.set_level(logging.INFO, logger="proofpilot.request")
    app.dependency_overrides[get_rate_limiter] = override_limiter
    app.dependency_overrides[get_settings] = lambda: Settings(proofpilot_rate_limiting_enabled=True)
    transport = ASGITransport(app=app, client=("203.0.113.30", 4567), raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/workspaces/workspace-a/query",
                json={"query": "Do not log AIzaSyD-example-secret-value-123456789"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 429
    payload = cast(dict[str, Any], json.loads(_request_log_messages(caplog)[0]))
    assert payload["path"] == "/api/v1/workspaces/workspace-a/query"
    assert payload["status_code"] == 429
    assert payload["rate_limited"] is True
    assert "AIzaSyD-example-secret-value" not in _request_log_messages(caplog)[0]


async def test_query_request_logging_includes_safe_query_run_metadata(
    caplog: LogCaptureFixture,
) -> None:
    class TelemetryQueryService:
        async def answer_workspace_query(
            self,
            *,
            workspace_id: str,
            query: str,
            mode: str,
        ) -> AnswerResponse:
            del workspace_id, query
            return AnswerResponse(
                query_run_id="query-run-log",
                answer_text="No reliable evidence was found.",
                citations=[],
                evidence_chunk_ids=[],
                confidence_label="low",
                refusal_reason="No reliable evidence was found.",
                generation_model_used="gemini-2.5-flash-lite",
                live_grounding_used=False,
                mode=mode,
                route="route_no_evidence",
                freshness_label="not_required",
                contradictions=[],
                cache_status="miss",
            )

    async def fake_query_service() -> TelemetryQueryService:
        return TelemetryQueryService()

    caplog.set_level(logging.INFO, logger="proofpilot.request")
    app.dependency_overrides[get_query_service] = fake_query_service
    app.dependency_overrides[get_settings] = lambda: Settings(
        proofpilot_rate_limiting_enabled=False
    )
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/workspaces/workspace-a/query",
                json={"query": "Do not log AIzaSyD-example-secret-value-123456789"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    message = _request_log_messages(caplog)[0]
    payload = cast(dict[str, Any], json.loads(message))
    assert payload["query_run_id"] == "query-run-log"
    assert payload["cache_status"] == "miss"
    assert payload["generation_model_used"] == "gemini-2.5-flash-lite"
    assert payload["live_grounding_used"] is False
    assert "Do not log" not in message
    assert "AIzaSyD-example-secret-value" not in message


def _request_log_messages(caplog: LogCaptureFixture) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.name == "proofpilot.request"]
