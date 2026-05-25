import asyncio
from pathlib import Path
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import build_embedding_provider
from app.core.config import Settings, get_settings
from app.db.session import create_session_factory
from app.ingestion.queue import IngestionQueue, RedisIngestionQueue
from app.services.documents import DocumentService
from app.services.embedding_index import EmbeddingIndexService
from app.vector.qdrant import QdrantVectorStore


class DocumentProcessor(Protocol):
    async def process_document(self, *, document_id: str) -> object: ...


async def process_next_job(
    *,
    queue: IngestionQueue,
    processor: DocumentProcessor,
    timeout_seconds: int,
) -> bool:
    document_id = await queue.reserve(timeout_seconds=timeout_seconds)
    if document_id is None:
        return False
    await processor.process_document(document_id=document_id)
    await queue.complete(document_id=document_id)
    return True


def build_document_processor(*, session: AsyncSession, settings: Settings) -> DocumentService:
    document_indexer = None
    if settings.upload_indexing_enabled:
        document_indexer = EmbeddingIndexService(
            session=session,
            embedding_provider=build_embedding_provider(settings),
            vector_store=QdrantVectorStore(
                url=settings.qdrant_url,
                collection=settings.qdrant_collection,
            ),
            embedding_model=(
                settings.gemini_embedding_model
                if settings.gemini_embeddings_enabled
                else "deterministic-local"
            ),
        )
    return DocumentService(session, Path(".data/uploads"), document_indexer=document_indexer)


async def run_worker() -> None:
    settings = get_settings()
    session_factory = create_session_factory(settings.database_url)
    queue = RedisIngestionQueue(url=settings.redis_url)
    try:
        await queue.recover_incomplete()
        while True:
            async with session_factory() as session:
                processor = build_document_processor(session=session, settings=settings)
                await process_next_job(queue=queue, processor=processor, timeout_seconds=5)
    finally:
        await queue.close()


if __name__ == "__main__":
    asyncio.run(run_worker())
