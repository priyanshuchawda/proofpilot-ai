from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.ai.embeddings import DeterministicEmbeddingProvider
from app.db.base import Base
from app.db.models import (
    Document,
    DocumentChunk,
    DocumentVersion,
    QueryRun,
    RetrievalCandidate,
    Workspace,
)
from app.services.embedding_index import EmbeddingIndexService
from app.services.retrieval import HybridRetrievalService
from app.vector.base import VectorPoint, VectorStore


class FakeVectorStore(VectorStore):
    def __init__(self, chunk_ids: list[str]) -> None:
        self.chunk_ids = chunk_ids

    async def ensure_collection(self, *, dimension: int) -> None:
        pass

    async def upsert(self, points: Sequence[VectorPoint]) -> None:
        pass

    async def search(self, *, vector: list[float], limit: int) -> list[str]:
        return self.chunk_ids[:limit]


async def _create_chunk(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    workspace_id: str,
    filename: str,
    text: str,
    order: int,
) -> DocumentChunk:
    async with session_factory() as session:
        document = Document(
            workspace_id=workspace_id,
            filename=filename,
            mime_type="text/markdown",
            status="ready",
        )
        session.add(document)
        await session.flush()
        version = DocumentVersion(
            document_id=document.id,
            content_hash=f"{filename}-hash",
            storage_path="memory",
            version_number=1,
        )
        session.add(version)
        await session.flush()
        chunk = DocumentChunk(
            workspace_id=workspace_id,
            document_id=document.id,
            document_version_id=version.id,
            source_filename=filename,
            mime_type=document.mime_type,
            page_number=None,
            section_heading="Notes",
            chunk_order=order,
            chunk_text=text,
            token_estimate=len(text.split()),
            content_hash=f"{filename}-chunk-{order}",
            redaction_status="clean",
        )
        session.add(chunk)
        await session.commit()
        return chunk


async def test_hybrid_retrieval_fuses_dense_and_keyword_candidates_and_stores_trace() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        workspace = Workspace(name="Retrieval", description=None)
        other_workspace = Workspace(name="Other", description=None)
        session.add_all([workspace, other_workspace])
        await session.commit()

    keyword_chunk = await _create_chunk(
        session_factory,
        workspace_id=workspace.id,
        filename="policy.md",
        text="ProofPilot keeps grounded evidence in a visible trace.",
        order=0,
    )
    dense_chunk = await _create_chunk(
        session_factory,
        workspace_id=workspace.id,
        filename="architecture.md",
        text="The architecture stores vector candidates for review.",
        order=1,
    )
    other_chunk = await _create_chunk(
        session_factory,
        workspace_id=other_workspace.id,
        filename="private.md",
        text="Grounded evidence from another workspace must not leak.",
        order=0,
    )

    async with session_factory() as session:
        embedding_service = EmbeddingIndexService(
            session=session,
            embedding_provider=DeterministicEmbeddingProvider(dimension=16),
            vector_store=FakeVectorStore([dense_chunk.id, keyword_chunk.id, other_chunk.id]),
            embedding_model="deterministic-local",
        )
        retrieval_service = HybridRetrievalService(
            session=session,
            embedding_service=embedding_service,
        )

        result = await retrieval_service.retrieve(
            workspace_id=workspace.id,
            query="grounded evidence trace",
            mode="verified",
            limit=3,
        )

        query_runs = (await session.execute(select(QueryRun))).scalars().all()
        candidates = (
            (await session.execute(select(RetrievalCandidate).order_by(RetrievalCandidate.rank)))
            .scalars()
            .all()
        )

    await engine.dispose()

    assert result.query_run_id == query_runs[0].id
    assert [evidence.chunk_id for evidence in result.evidence] == [
        keyword_chunk.id,
        dense_chunk.id,
    ]
    assert all(evidence.workspace_id == workspace.id for evidence in result.evidence)
    assert other_chunk.id not in [evidence.chunk_id for evidence in result.evidence]
    assert len(candidates) == 2
    assert candidates[0].source == "hybrid"
    assert candidates[0].chunk_id == keyword_chunk.id


async def test_hybrid_retrieval_returns_empty_evidence_and_query_run_when_no_match() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        workspace = Workspace(name="Retrieval", description=None)
        session.add(workspace)
        await session.commit()

    await _create_chunk(
        session_factory,
        workspace_id=workspace.id,
        filename="policy.md",
        text="ProofPilot stores evidence.",
        order=0,
    )

    async with session_factory() as session:
        embedding_service = EmbeddingIndexService(
            session=session,
            embedding_provider=DeterministicEmbeddingProvider(dimension=16),
            vector_store=FakeVectorStore([]),
            embedding_model="deterministic-local",
        )
        retrieval_service = HybridRetrievalService(
            session=session,
            embedding_service=embedding_service,
        )

        result = await retrieval_service.retrieve(
            workspace_id=workspace.id,
            query="unrelated zyxwvu",
            mode="verified",
            limit=3,
        )

        query_runs = (await session.execute(select(QueryRun))).scalars().all()
        candidates = (await session.execute(select(RetrievalCandidate))).scalars().all()

    await engine.dispose()

    assert result.evidence == []
    assert len(query_runs) == 1
    assert candidates == []
