from httpx import ASGITransport, AsyncClient

from app.answers.schemas import AnswerResponse, Citation
from app.api.query import get_query_service
from app.main import app


class FakeQueryService:
    async def answer_workspace_query(
        self,
        *,
        workspace_id: str,
        query: str,
        mode: str,
    ) -> AnswerResponse:
        return AnswerResponse(
            query_run_id="query-run-a",
            answer_text=f"Answer for {workspace_id}: {query} [chunk-a]",
            citations=[
                Citation(
                    chunk_id="chunk-a",
                    source_filename="policy.md",
                    page_number=None,
                    section_heading="Policy",
                    evidence_text="Grounded evidence.",
                )
            ],
            evidence_chunk_ids=["chunk-a"],
            confidence_label="medium",
            refusal_reason=None,
            mode=mode,
            route="route_document_verified",
            freshness_label="not_required",
            contradictions=[],
        )


async def test_query_endpoint_returns_structured_cited_answer() -> None:
    async def fake_query_service() -> FakeQueryService:
        return FakeQueryService()

    app.dependency_overrides[get_query_service] = fake_query_service
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/workspaces/workspace-a/query",
                json={"query": "What does the policy say?", "mode": "verified"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["query_run_id"] == "query-run-a"
    assert payload["answer_text"] == "Answer for workspace-a: What does the policy say? [chunk-a]"
    assert payload["citations"][0]["chunk_id"] == "chunk-a"
    assert payload["evidence_chunk_ids"] == ["chunk-a"]


async def test_query_stream_endpoint_returns_sse_answer_events() -> None:
    async def fake_query_service() -> FakeQueryService:
        return FakeQueryService()

    app.dependency_overrides[get_query_service] = fake_query_service
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/workspaces/workspace-a/query/stream",
                json={"query": "What does the policy say?", "mode": "verified"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'event: answer_delta\ndata: {"text":"Answer "}' in response.text
    assert "event: final" in response.text
    assert '"query_run_id":"query-run-a"' in response.text
