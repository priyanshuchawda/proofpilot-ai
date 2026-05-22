import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.infra.health import check_dependencies
from app.main import app


@pytest.mark.skipif(
    os.getenv("RUN_INFRA_INTEGRATION") != "1",
    reason="Docker-backed infrastructure tests are opt-in.",
)
async def test_docker_backed_dependency_health() -> None:
    results = await check_dependencies()

    assert {result.name: result.status for result in results} == {
        "postgres": "ok",
        "redis": "ok",
        "qdrant": "ok",
    }


@pytest.mark.skipif(
    os.getenv("RUN_INFRA_INTEGRATION") != "1",
    reason="Docker-backed infrastructure tests are opt-in.",
)
async def test_docker_backed_workspace_api_persists_to_postgres() -> None:
    workspace_name = f"Integration {uuid4()}"
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        create_response = await client.post(
            "/api/v1/workspaces",
            json={"name": workspace_name, "description": "Docker-backed persistence"},
        )
        list_response = await client.get("/api/v1/workspaces")

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == workspace_name

    assert list_response.status_code == 200
    assert created in list_response.json()
