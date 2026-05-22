from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.embeddings import DeterministicEmbeddingProvider
from app.db.base import Base
from app.db.models import Document, DocumentChunk, DocumentVersion, EmbeddingRecord, Workspace
from app.services.embedding_index import EmbeddingIndexService
from app.vector.base import VectorPoint, VectorStore


class FakeVectorStore(VectorStore):
    def __init__(self) -> None:
        self.points: list[VectorPoint] = []
        self.dimension: int | None = None
        self.searched_vectors: list[list[float]] = []

    async def ensure_collection(self, *, dimension: int) -> None:
        self.dimension = dimension

    async def upsert(self, points: Sequence[VectorPoint]) -> None:
        self.points.extend(points)

    async def search(self, *, vector: list[float], limit: int) -> list[str]:
        self.searched_vectors.append(vector)
        return [point.chunk_id for point in self.points[:limit]]


async def test_embedding_index_service_persists_records_and_upserts_vectors() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        workspace = Workspace(name="Index", description=None)
        session.add(workspace)
        await session.flush()
        document = Document(
            workspace_id=workspace.id,
            filename="evidence.md",
            mime_type="text/markdown",
            status="ready",
        )
        session.add(document)
        await session.flush()
        version = DocumentVersion(
            document_id=document.id,
            content_hash="doc-hash",
            storage_path="memory",
            version_number=1,
        )
        session.add(version)
        await session.flush()
        chunk = DocumentChunk(
            workspace_id=workspace.id,
            document_id=document.id,
            document_version_id=version.id,
            source_filename=document.filename,
            mime_type=document.mime_type,
            page_number=None,
            section_heading="Evidence",
            chunk_order=0,
            chunk_text="ProofPilot stores grounded evidence.",
            token_estimate=8,
            content_hash="chunk-hash",
            redaction_status="clean",
        )
        session.add(chunk)
        await session.commit()

        vector_store = FakeVectorStore()
        service = EmbeddingIndexService(
            session=session,
            embedding_provider=DeterministicEmbeddingProvider(dimension=16),
            vector_store=vector_store,
            embedding_model="deterministic-local",
        )

        indexed = await service.index_document(document_id=document.id)

        records = (await session.execute(select(EmbeddingRecord))).scalars().all()

    await engine.dispose()

    assert indexed == 1
    assert len(records) == 1
    assert records[0].chunk_id == chunk.id
    assert records[0].dimension == 16
    assert len(vector_store.points) == 1
    assert vector_store.points[0].chunk_id == chunk.id


async def test_embedding_index_service_skips_existing_content_hash_records() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        workspace = Workspace(name="Index", description=None)
        session.add(workspace)
        await session.flush()
        document = Document(
            workspace_id=workspace.id,
            filename="evidence.md",
            mime_type="text/markdown",
            status="ready",
        )
        session.add(document)
        await session.flush()
        version = DocumentVersion(
            document_id=document.id,
            content_hash="doc-hash",
            storage_path="memory",
            version_number=1,
        )
        session.add(version)
        await session.flush()
        chunk = DocumentChunk(
            workspace_id=workspace.id,
            document_id=document.id,
            document_version_id=version.id,
            source_filename=document.filename,
            mime_type=document.mime_type,
            page_number=None,
            section_heading="Evidence",
            chunk_order=0,
            chunk_text="ProofPilot stores grounded evidence.",
            token_estimate=8,
            content_hash="chunk-hash",
            redaction_status="clean",
        )
        session.add(chunk)
        await session.flush()
        session.add(
            EmbeddingRecord(
                chunk_id=chunk.id,
                model="deterministic-local",
                vector_id="existing-vector",
                dimension=16,
                content_hash=chunk.content_hash,
            )
        )
        await session.commit()

        vector_store = FakeVectorStore()
        service = EmbeddingIndexService(
            session=session,
            embedding_provider=DeterministicEmbeddingProvider(dimension=16),
            vector_store=vector_store,
            embedding_model="deterministic-local",
        )

        indexed = await service.index_document(document_id=document.id)

        records = (await session.execute(select(EmbeddingRecord))).scalars().all()

    await engine.dispose()

    assert indexed == 0
    assert len(records) == 1
    assert vector_store.points == []


async def test_embedding_index_service_embeds_query_before_vector_search() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        vector_store = FakeVectorStore()
        vector_store.points.append(
            VectorPoint(point_id="point-a", chunk_id="chunk-a", vector=[1.0] * 16)
        )
        service = EmbeddingIndexService(
            session=session,
            embedding_provider=DeterministicEmbeddingProvider(dimension=16),
            vector_store=vector_store,
            embedding_model="deterministic-local",
        )

        results = await service.search_query(query="grounded evidence", limit=1)

    await engine.dispose()

    assert results == ["chunk-a"]
    assert len(vector_store.searched_vectors) == 1
    assert len(vector_store.searched_vectors[0]) == 16
