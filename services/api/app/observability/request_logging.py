import json
import logging
import re
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


class RequestLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._logger = logging.getLogger("proofpilot.request")

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = _request_id_from_header(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        started_at = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            self._log_request(
                request=request,
                request_id=request_id,
                status_code=status_code,
                duration_ms=_elapsed_ms(started_at),
            )
            raise

        response.headers[REQUEST_ID_HEADER] = request_id
        self._log_request(
            request=request,
            request_id=request_id,
            status_code=status_code,
            duration_ms=_elapsed_ms(started_at),
        )
        return response

    def _log_request(
        self,
        *,
        request: Request,
        request_id: str,
        status_code: int,
        duration_ms: int,
    ) -> None:
        payload = {
            "duration_ms": duration_ms,
            "event": "http_request",
            "method": request.method,
            "path": request.url.path,
            "rate_limited": status_code == 429,
            "request_id": request_id,
            "status_code": status_code,
        }
        for field in (
            "cache_status",
            "generation_model_used",
            "live_grounding_used",
            "query_run_id",
        ):
            value = getattr(request.state, field, None)
            if value is not None:
                payload[field] = value
        self._logger.info(json.dumps(payload, separators=(",", ":"), sort_keys=True))


def _request_id_from_header(value: str | None) -> str:
    if value and _REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return uuid4().hex


def _elapsed_ms(started_at: float) -> int:
    return max(0, int((perf_counter() - started_at) * 1000))
