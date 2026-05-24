import os
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.embeddings import DeterministicEmbeddingProvider
from app.db.base import Base
from app.db.models import Workspace
from app.services.documents import DocumentService
from app.services.embedding_index import EmbeddingIndexService
from app.vector.base import VectorPoint
from app.vector.qdrant import QdrantCollectionConfigurationError, QdrantVectorStore


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


@pytest.mark.skipif(
    os.getenv("RUN_INFRA_INTEGRATION") != "1",
    reason="Docker-backed Qdrant tests are opt-in.",
)
async def test_qdrant_vector_store_rejects_existing_collection_dimension_mismatch() -> None:
    store = QdrantVectorStore(
        url=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"),
        collection=f"proofpilot_test_{uuid4().hex}",
    )

    await store.ensure_collection(dimension=4)

    with pytest.raises(QdrantCollectionConfigurationError, match="configured dimension is 8"):
        await store.ensure_collection(dimension=8)


@pytest.mark.skipif(
    os.getenv("RUN_INFRA_INTEGRATION") != "1",
    reason="Docker-backed Qdrant tests are opt-in.",
)
async def test_qdrant_vector_store_rejects_existing_collection_distance_mismatch() -> None:
    qdrant_url = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
    collection = f"proofpilot_test_{uuid4().hex}"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.put(
            f"{qdrant_url}/collections/{collection}",
            json={"vectors": {"size": 4, "distance": "Dot"}},
        )
    response.raise_for_status()
    store = QdrantVectorStore(url=qdrant_url, collection=collection)

    with pytest.raises(QdrantCollectionConfigurationError, match="distance"):
        await store.ensure_collection(dimension=4)


@pytest.mark.skipif(
    os.getenv("RUN_INFRA_INTEGRATION") != "1",
    reason="Docker-backed Qdrant tests are opt-in.",
)
async def test_document_indexing_reuses_existing_qdrant_collection(tmp_path: Path) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        workspace = Workspace(name="Indexed documents", description=None)
        session.add(workspace)
        await session.commit()

        indexer = EmbeddingIndexService(
            session=session,
            embedding_provider=DeterministicEmbeddingProvider(dimension=16),
            vector_store=QdrantVectorStore(
                url=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"),
                collection=f"proofpilot_test_{uuid4().hex}",
            ),
            embedding_model="deterministic-local",
        )
        service = DocumentService(session, tmp_path, document_indexer=indexer)
        first = await service.ingest_upload(
            workspace_id=workspace.id,
            filename="one.md",
            content_type="text/markdown",
            content=b"# One\nPublic evidence one.",
        )
        second = await service.ingest_upload(
            workspace_id=workspace.id,
            filename="two.md",
            content_type="text/markdown",
            content=b"# Two\nPublic evidence two.",
        )

    await engine.dispose()

    assert first.status == "ready"
    assert second.status == "ready"
