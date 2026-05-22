"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def id_column() -> sa.Column[str]:
    return sa.Column("id", sa.String(length=36), primary_key=True)


def timestamps() -> tuple[sa.Column[sa.DateTime], sa.Column[sa.DateTime]]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "workspaces",
        id_column(),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        *timestamps(),
    )
    op.create_table(
        "documents",
        id_column(),
        sa.Column(
            "workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column("filename", sa.String(length=260), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("current_version_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_documents_workspace_id", "documents", ["workspace_id"])
    op.create_table(
        "document_versions",
        id_column(),
        sa.Column(
            "document_id", sa.String(length=36), sa.ForeignKey("documents.id"), nullable=False
        ),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    op.create_table(
        "ingestion_jobs",
        id_column(),
        sa.Column(
            "document_version_id",
            sa.String(length=36),
            sa.ForeignKey("document_versions.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        *timestamps(),
    )
    op.create_index(
        "ix_ingestion_jobs_document_version_id", "ingestion_jobs", ["document_version_id"]
    )
    op.create_table(
        "document_chunks",
        id_column(),
        sa.Column(
            "workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column(
            "document_id", sa.String(length=36), sa.ForeignKey("documents.id"), nullable=False
        ),
        sa.Column(
            "document_version_id",
            sa.String(length=36),
            sa.ForeignKey("document_versions.id"),
            nullable=False,
        ),
        sa.Column("source_filename", sa.String(length=260), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section_heading", sa.Text(), nullable=True),
        sa.Column("chunk_order", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("redaction_status", sa.String(length=40), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("document_version_id", "chunk_order", name="uq_chunk_version_order"),
    )
    op.create_index("ix_document_chunks_workspace_id", "document_chunks", ["workspace_id"])
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index(
        "ix_document_chunks_document_version_id", "document_chunks", ["document_version_id"]
    )
    op.create_table(
        "embedding_records",
        id_column(),
        sa.Column(
            "chunk_id", sa.String(length=36), sa.ForeignKey("document_chunks.id"), nullable=False
        ),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("vector_id", sa.String(length=120), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_embedding_records_chunk_id", "embedding_records", ["chunk_id"])
    op.create_table(
        "conversations",
        id_column(),
        sa.Column(
            "workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column("title", sa.String(length=240), nullable=True),
        *timestamps(),
    )
    op.create_index("ix_conversations_workspace_id", "conversations", ["workspace_id"])
    op.create_table(
        "messages",
        id_column(),
        sa.Column(
            "conversation_id",
            sa.String(length=36),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_table(
        "query_runs",
        id_column(),
        sa.Column(
            "workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column(
            "conversation_id",
            sa.String(length=36),
            sa.ForeignKey("conversations.id"),
            nullable=True,
        ),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("route", sa.String(length=80), nullable=False),
        sa.Column("mode", sa.String(length=40), nullable=False),
        sa.Column("cache_status", sa.String(length=40), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_query_runs_workspace_id", "query_runs", ["workspace_id"])
    op.create_table(
        "retrieval_candidates",
        id_column(),
        sa.Column(
            "query_run_id", sa.String(length=36), sa.ForeignKey("query_runs.id"), nullable=False
        ),
        sa.Column(
            "chunk_id", sa.String(length=36), sa.ForeignKey("document_chunks.id"), nullable=False
        ),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.String(length=80), nullable=False),
        *timestamps(),
    )
    op.create_index(
        "ix_retrieval_candidates_query_run_id", "retrieval_candidates", ["query_run_id"]
    )
    op.create_index("ix_retrieval_candidates_chunk_id", "retrieval_candidates", ["chunk_id"])
    op.create_table(
        "cited_evidence",
        id_column(),
        sa.Column(
            "query_run_id", sa.String(length=36), sa.ForeignKey("query_runs.id"), nullable=False
        ),
        sa.Column(
            "chunk_id", sa.String(length=36), sa.ForeignKey("document_chunks.id"), nullable=True
        ),
        sa.Column("citation_label", sa.String(length=80), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("source_kind", sa.String(length=40), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_cited_evidence_query_run_id", "cited_evidence", ["query_run_id"])
    op.create_table(
        "generated_answers",
        id_column(),
        sa.Column(
            "query_run_id", sa.String(length=36), sa.ForeignKey("query_runs.id"), nullable=False
        ),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("confidence_label", sa.String(length=40), nullable=False),
        sa.Column("refusal_reason", sa.Text(), nullable=True),
        sa.Column("live_grounding_used", sa.Boolean(), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_generated_answers_query_run_id", "generated_answers", ["query_run_id"])
    op.create_table(
        "verification_results",
        id_column(),
        sa.Column(
            "query_run_id", sa.String(length=36), sa.ForeignKey("query_runs.id"), nullable=False
        ),
        sa.Column("citation_valid", sa.Boolean(), nullable=False),
        sa.Column("unsupported_claim_count", sa.Integer(), nullable=False),
        sa.Column("contradiction_count", sa.Integer(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        *timestamps(),
    )
    op.create_index(
        "ix_verification_results_query_run_id", "verification_results", ["query_run_id"]
    )
    op.create_table(
        "cache_entry_metadata",
        id_column(),
        sa.Column(
            "workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column("cache_key", sa.String(length=256), nullable=False, unique=True),
        sa.Column("cache_type", sa.String(length=60), nullable=False),
        sa.Column("ttl_seconds", sa.Integer(), nullable=False),
        *timestamps(),
    )
    op.create_index(
        "ix_cache_entry_metadata_workspace_id", "cache_entry_metadata", ["workspace_id"]
    )
    op.create_table(
        "evaluation_cases",
        id_column(),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("input_query", sa.Text(), nullable=False),
        sa.Column("expected_behavior", sa.Text(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "evaluation_runs",
        id_column(),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "latency_metrics",
        id_column(),
        sa.Column(
            "query_run_id", sa.String(length=36), sa.ForeignKey("query_runs.id"), nullable=True
        ),
        sa.Column("metric_name", sa.String(length=120), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        *timestamps(),
    )


def downgrade() -> None:
    for table in (
        "latency_metrics",
        "evaluation_runs",
        "evaluation_cases",
        "cache_entry_metadata",
        "verification_results",
        "generated_answers",
        "cited_evidence",
        "retrieval_candidates",
        "query_runs",
        "messages",
        "conversations",
        "embedding_records",
        "document_chunks",
        "ingestion_jobs",
        "document_versions",
        "documents",
        "workspaces",
    ):
        op.drop_table(table)
