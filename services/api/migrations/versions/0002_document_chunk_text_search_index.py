"""document chunk full-text search index

Revision ID: 0002_chunk_fts_index
Revises: 0001_initial_schema
Create Date: 2026-05-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_chunk_fts_index"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX ix_document_chunks_search_vector
        ON document_chunks
        USING GIN (
            to_tsvector(
                'english'::regconfig,
                coalesce(section_heading, '') || ' ' || chunk_text
            )
        )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_search_vector", table_name="document_chunks")
