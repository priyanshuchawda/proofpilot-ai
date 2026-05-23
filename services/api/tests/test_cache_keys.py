from app.answers.schemas import AnswerResponse
from app.cache.backends import InMemoryCacheBackend
from app.cache.keys import response_cache_key, retrieval_cache_key
from app.cache.policy import can_cache_response


def test_retrieval_cache_key_is_scoped_by_workspace_and_index_version() -> None:
    first = retrieval_cache_key(
        workspace_id="workspace-a",
        index_version="v1",
        query="What is the policy?",
        retrieval_config={"mode": "fast", "limit": 3},
    )
    second = retrieval_cache_key(
        workspace_id="workspace-b",
        index_version="v1",
        query="What is the policy?",
        retrieval_config={"mode": "fast", "limit": 3},
    )
    third = retrieval_cache_key(
        workspace_id="workspace-a",
        index_version="v2",
        query="What is the policy?",
        retrieval_config={"mode": "fast", "limit": 3},
    )

    assert first != second
    assert first != third


def test_response_cache_key_is_stable_for_same_workspace_query_and_config() -> None:
    first = response_cache_key(
        workspace_id="workspace-a",
        index_version="v1",
        query="What is the policy?",
        mode="fast",
    )
    second = response_cache_key(
        workspace_id="workspace-a",
        index_version="v1",
        query="What is the policy?",
        mode="fast",
    )

    assert first == second


def test_response_cache_policy_rejects_freshness_and_refusals() -> None:
    answer = AnswerResponse(
        query_run_id="query-run-a",
        answer_text="Answer [chunk-a]",
        citations=[],
        evidence_chunk_ids=["chunk-a"],
        confidence_label="medium",
        refusal_reason=None,
        mode="fast",
        route="route_document_fast",
        freshness_label="not_required",
        contradictions=[],
    )

    assert can_cache_response(answer)
    assert not can_cache_response(answer.model_copy(update={"route": "route_freshness_required"}))
    assert not can_cache_response(answer.model_copy(update={"refusal_reason": "No evidence."}))


async def test_in_memory_cache_honors_ttl() -> None:
    cache = InMemoryCacheBackend()

    await cache.set_json("key", {"value": "cached"}, ttl_seconds=0)

    assert await cache.get_json("key") is None
