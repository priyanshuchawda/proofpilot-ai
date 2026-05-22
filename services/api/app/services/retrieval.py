import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentChunk, QueryRun, RetrievalCandidate
from app.retrieval.fusion import RankedCandidate, fuse_ranked_candidates
from app.retrieval.schemas import EvidenceChunk, RetrievalResult
from app.services.embedding_index import EmbeddingIndexService

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class HybridRetrievalService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        embedding_service: EmbeddingIndexService,
        dense_limit: int = 12,
        keyword_limit: int = 12,
    ) -> None:
        self._session = session
        self._embedding_service = embedding_service
        self._dense_limit = dense_limit
        self._keyword_limit = keyword_limit

    async def retrieve(
        self,
        *,
        workspace_id: str,
        query: str,
        mode: str,
        limit: int,
    ) -> RetrievalResult:
        query_run = QueryRun(
            workspace_id=workspace_id,
            conversation_id=None,
            query_text=query,
            route="route_document_verified",
            mode=mode,
            cache_status="miss",
        )
        self._session.add(query_run)
        await self._session.flush()

        dense = await self._dense_candidates(workspace_id=workspace_id, query=query)
        keyword = await self._keyword_candidates(workspace_id=workspace_id, query=query)
        fused = fuse_ranked_candidates(dense=dense, keyword=keyword, limit=limit)

        chunks = await self._chunks_by_id(
            workspace_id=workspace_id,
            chunk_ids=[candidate.chunk_id for candidate in fused],
        )
        evidence: list[EvidenceChunk] = []
        for candidate in fused:
            chunk = chunks.get(candidate.chunk_id)
            if chunk is None:
                continue
            self._session.add(
                RetrievalCandidate(
                    query_run_id=query_run.id,
                    chunk_id=candidate.chunk_id,
                    source=candidate.source,
                    rank=candidate.rank,
                    score=f"{candidate.score:.8f}",
                )
            )
            evidence.append(
                EvidenceChunk(
                    chunk_id=chunk.id,
                    workspace_id=chunk.workspace_id,
                    document_id=chunk.document_id,
                    document_version_id=chunk.document_version_id,
                    source_filename=chunk.source_filename,
                    mime_type=chunk.mime_type,
                    page_number=chunk.page_number,
                    section_heading=chunk.section_heading,
                    chunk_order=chunk.chunk_order,
                    text=chunk.chunk_text,
                    score=candidate.score,
                    source=candidate.source,
                )
            )

        await self._session.commit()
        return RetrievalResult(query_run_id=query_run.id, evidence=evidence)

    async def _dense_candidates(
        self,
        *,
        workspace_id: str,
        query: str,
    ) -> list[RankedCandidate]:
        chunk_ids = await self._embedding_service.search_query(
            query=query,
            limit=self._dense_limit,
        )
        chunks = await self._chunks_by_id(workspace_id=workspace_id, chunk_ids=chunk_ids)
        return [
            RankedCandidate(chunk_id=chunk_id, source="dense", rank=rank, score=1.0 / rank)
            for rank, chunk_id in enumerate(chunk_ids, start=1)
            if chunk_id in chunks
        ]

    async def _keyword_candidates(
        self,
        *,
        workspace_id: str,
        query: str,
    ) -> list[RankedCandidate]:
        query_terms = set(_tokens(query))
        if not query_terms:
            return []

        chunks = (
            (
                await self._session.execute(
                    select(DocumentChunk)
                    .where(DocumentChunk.workspace_id == workspace_id)
                    .order_by(DocumentChunk.chunk_order)
                )
            )
            .scalars()
            .all()
        )
        scored: list[tuple[DocumentChunk, float]] = []
        for chunk in chunks:
            chunk_terms = set(_tokens(chunk.chunk_text))
            overlap = len(query_terms & chunk_terms)
            if overlap == 0:
                continue
            phrase_bonus = 1.0 if query.lower() in chunk.chunk_text.lower() else 0.0
            scored.append((chunk, float(overlap) + phrase_bonus))

        scored.sort(key=lambda item: (-item[1], item[0].chunk_order, item[0].id))
        return [
            RankedCandidate(
                chunk_id=chunk.id,
                source="keyword",
                rank=rank,
                score=score,
            )
            for rank, (chunk, score) in enumerate(scored[: self._keyword_limit], start=1)
        ]

    async def _chunks_by_id(
        self,
        *,
        workspace_id: str,
        chunk_ids: list[str],
    ) -> dict[str, DocumentChunk]:
        if not chunk_ids:
            return {}
        chunks = (
            (
                await self._session.execute(
                    select(DocumentChunk).where(
                        DocumentChunk.workspace_id == workspace_id,
                        DocumentChunk.id.in_(chunk_ids),
                    )
                )
            )
            .scalars()
            .all()
        )
        return {chunk.id: chunk for chunk in chunks}


def _tokens(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())
