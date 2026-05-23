from uuid import uuid4

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import EmbeddingProvider, EmbeddingRequest
from app.db.models import DocumentChunk, EmbeddingRecord
from app.vector.base import VectorPoint, VectorStore


class EmbeddingIndexService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        embedding_model: str,
    ) -> None:
        self._session = session
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._embedding_model = embedding_model

    async def index_document(self, *, document_id: str) -> int:
        chunks = (
            (
                await self._session.execute(
                    select(DocumentChunk)
                    .where(DocumentChunk.document_id == document_id)
                    .order_by(DocumentChunk.chunk_order)
                )
            )
            .scalars()
            .all()
        )
        if not chunks:
            return 0

        chunk_keys = [(chunk.id, chunk.content_hash) for chunk in chunks]
        existing_keys = set(
            (
                await self._session.execute(
                    select(EmbeddingRecord.chunk_id, EmbeddingRecord.content_hash).where(
                        EmbeddingRecord.model == self._embedding_model,
                        tuple_(
                            EmbeddingRecord.chunk_id,
                            EmbeddingRecord.content_hash,
                        ).in_(chunk_keys),
                    )
                )
            ).all()
        )
        chunks_to_embed = [
            chunk for chunk in chunks if (chunk.id, chunk.content_hash) not in existing_keys
        ]
        if not chunks_to_embed:
            return 0

        embedding_response = await self._embedding_provider.embed_texts(
            EmbeddingRequest(
                texts=[chunk.chunk_text for chunk in chunks_to_embed],
                model=self._embedding_model,
                kind="document",
            )
        )
        await self._vector_store.ensure_collection(dimension=embedding_response.dimension)

        points: list[VectorPoint] = []
        for chunk, vector in zip(chunks_to_embed, embedding_response.vectors, strict=True):
            point_id = str(uuid4())
            points.append(VectorPoint(point_id=point_id, chunk_id=chunk.id, vector=vector))
            self._session.add(
                EmbeddingRecord(
                    chunk_id=chunk.id,
                    model=embedding_response.model,
                    vector_id=point_id,
                    dimension=embedding_response.dimension,
                    content_hash=chunk.content_hash,
                )
            )

        await self._vector_store.upsert(points)
        await self._session.commit()
        return len(points)

    async def search_query(self, *, query: str, limit: int) -> list[str]:
        embedding_response = await self._embedding_provider.embed_texts(
            EmbeddingRequest(texts=[query], model=self._embedding_model, kind="query")
        )
        return await self._vector_store.search(
            vector=embedding_response.vectors[0],
            limit=limit,
        )
