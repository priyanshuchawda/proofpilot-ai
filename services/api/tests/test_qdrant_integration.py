import os
from uuid import uuid4

import pytest

from app.vector.base import VectorPoint
from app.vector.qdrant import QdrantVectorStore


@pytest.mark.skipif(
    os.getenv("RUN_INFRA_INTEGRATION") != "1",
    reason="Docker-backed Qdrant tests are opt-in.",
)
async def test_qdrant_vector_store_upserts_and_searches() -> None:
    collection = f"proofpilot_test_{uuid4().hex}"
    store = QdrantVectorStore(
        url=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"),
        collection=collection,
    )

    await store.ensure_collection(dimension=4)
    await store.upsert(
        [
            VectorPoint(
                point_id=str(uuid4()),
                chunk_id="chunk-a",
                vector=[1.0, 0.0, 0.0, 0.0],
            ),
            VectorPoint(
                point_id=str(uuid4()),
                chunk_id="chunk-b",
                vector=[0.0, 1.0, 0.0, 0.0],
            ),
        ]
    )

    results = await store.search(vector=[1.0, 0.0, 0.0, 0.0], limit=1)

    assert results == ["chunk-a"]
