import re
from typing import Protocol

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentChunk
from app.retrieval.fusion import RankedCandidate

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class KeywordRetriever(Protocol):
    async def retrieve(
        self,
        *,
        workspace_id: str,
        query: str,
        limit: int,
    ) -> list[RankedCandidate]: ...


class PostgresKeywordRetriever:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def retrieve(
        self,
        *,
        workspace_id: str,
        query: str,
        limit: int,
    ) -> list[RankedCandidate]:
        if not query.strip():
            return []

        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT id,
                           ts_rank_cd(
                               to_tsvector(
                                   'english'::regconfig,
                                   coalesce(section_heading, '') || ' ' || chunk_text
                               ),
                               websearch_to_tsquery('english'::regconfig, :query)
                           ) AS score
                    FROM document_chunks
                    WHERE workspace_id = :workspace_id
                      AND to_tsvector(
                              'english'::regconfig,
                              coalesce(section_heading, '') || ' ' || chunk_text
                          ) @@ websearch_to_tsquery('english'::regconfig, :query)
                    ORDER BY score DESC, chunk_order ASC, id ASC
                    LIMIT :limit
                    """
                ),
                {"workspace_id": workspace_id, "query": query, "limit": limit},
            )
        ).all()
        return [
            RankedCandidate(
                chunk_id=str(row.id),
                source="keyword",
                rank=rank,
                score=float(row.score),
            )
            for rank, row in enumerate(rows, start=1)
        ]


class DeterministicKeywordRetriever:
    """Portable exact-term scoring for unit tests that use SQLite."""

    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def retrieve(
        self,
        *,
        workspace_id: str,
        query: str,
        limit: int,
    ) -> list[RankedCandidate]:
        query_terms = set(TOKEN_PATTERN.findall(query.lower()))
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
            chunk_terms = set(TOKEN_PATTERN.findall(chunk.chunk_text.lower()))
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
            for rank, (chunk, score) in enumerate(scored[:limit], start=1)
        ]
