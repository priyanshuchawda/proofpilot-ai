import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


async def test_configured_cors_origin_is_allowed_without_allowing_other_origins() -> None:
    app = create_app(
        Settings(
            proofpilot_api_cors_origins="http://127.0.0.1:3011",
        )
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        allowed = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://127.0.0.1:3011",
                "Access-Control-Request-Method": "GET",
            },
        )
        rejected = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://127.0.0.1:3012",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:3011"
    assert "access-control-allow-origin" not in rejected.headers


def test_cors_origins_reject_wildcards() -> None:
    with pytest.raises(ValidationError):
        Settings(proofpilot_api_cors_origins="*")
