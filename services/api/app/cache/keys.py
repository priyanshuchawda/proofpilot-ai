import hashlib
import json
from typing import Any


def retrieval_cache_key(
    *,
    workspace_id: str,
    index_version: str,
    query: str,
    retrieval_config: dict[str, Any],
) -> str:
    payload = {
        "query": query.strip().lower(),
        "retrieval_config": retrieval_config,
    }
    return f"retrieval:{index_version}:{workspace_id}:{_digest(payload)}"


def response_cache_key(
    *,
    workspace_id: str,
    index_version: str,
    query: str,
    mode: str,
) -> str:
    payload = {"query": query.strip().lower()}
    return f"response:{index_version}:{workspace_id}:{mode}:{_digest(payload)}"


def _digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
