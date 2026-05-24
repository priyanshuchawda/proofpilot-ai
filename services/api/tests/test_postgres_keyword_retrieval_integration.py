import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Document, DocumentChunk, DocumentVersion, Workspace
from app.retrieval.keyword import PostgresKeywordRetriever


async def _create_chunk(
    session: AsyncSession,
    *,
    workspace_id: str,
    filename: str,
    text_value: str,
) -> DocumentChunk:
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
        content_hash=f"{filename}-{uuid4().hex}",
        storage_path="integration-test",
        version_number=1,
    )
    session.add(version)
    await session.flush()
    chunk = DocumentChunk(
        workspace_id=workspace_id,
        document_id=document.id,
        document_version_id=version.id,
        source_filename=filename,
        mime_type="text/markdown",
        page_number=None,
        section_heading="Policy",
        chunk_order=0,
        chunk_text=text_value,
        token_estimate=len(text_value.split()),
        content_hash=f"chunk-{uuid4().hex}",
        redaction_status="clean",
    )
    session.add(chunk)
    await session.flush()
    return chunk


@pytest.mark.skipif(
    os.getenv("RUN_INFRA_INTEGRATION") != "1",
    reason="Docker-backed PostgreSQL tests are opt-in.",
)
async def test_postgres_keyword_retrieval_stems_terms_and_scopes_workspace() -> None:
    engine = create_async_engine(
        os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://proofpilot:proofpilot@127.0.0.1:55432/proofpilot",
        )
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        workspace = Workspace(name=f"Keyword {uuid4()}", description=None)
        other_workspace = Workspace(name=f"Other {uuid4()}", description=None)
        session.add_all([workspace, other_workspace])
        await session.flush()
        matching = await _create_chunk(
            session,
            workspace_id=workspace.id,
            filename="decision.md",
            text_value="A documented decision is supported by public evidence.",
        )
        await _create_chunk(
            session,
            workspace_id=other_workspace.id,
            filename="other.md",
            text_value="Decisions from another workspace must never be returned.",
        )
        await session.commit()

        candidates = await PostgresKeywordRetriever(session=session).retrieve(
            workspace_id=workspace.id,
            query="decisions",
            limit=3,
        )

    await engine.dispose()

    assert [candidate.chunk_id for candidate in candidates] == [matching.id]
    assert candidates[0].source == "keyword"
    assert candidates[0].score > 0


@pytest.mark.skipif(
    os.getenv("RUN_INFRA_INTEGRATION") != "1",
    reason="Docker-backed PostgreSQL tests are opt-in.",
)
async def test_postgres_document_chunk_text_search_index_exists() -> None:
    engine = create_async_engine(
        os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://proofpilot:proofpilot@127.0.0.1:55432/proofpilot",
        )
    )
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE tablename = 'document_chunks' "
                "AND indexname = 'ix_document_chunks_search_vector'"
            )
        )
        index_definition = result.scalar_one_or_none()
    await engine.dispose()

    assert index_definition is not None
    assert "using gin" in index_definition.lower()
