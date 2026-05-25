from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class Workspace(TimestampMixin, Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner_session_id: Mapped[str] = mapped_column(
        String(128), nullable=False, default="local-anonymous", index=True
    )


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    filename: Mapped[str] = mapped_column(String(260), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    current_version_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(40), default="uploaded")


class DocumentVersion(TimestampMixin, Base):
    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)


class IngestionJob(TimestampMixin, Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)


class DocumentChunk(TimestampMixin, Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_version_id", "chunk_order", name="uq_chunk_version_order"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), index=True)
    source_filename: Mapped[str] = mapped_column(String(260), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    section_heading: Mapped[str | None] = mapped_column(Text)
    chunk_order: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    redaction_status: Mapped[str] = mapped_column(String(40), default="not_required")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EmbeddingRecord(TimestampMixin, Base):
    __tablename__ = "embedding_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    chunk_id: Mapped[str] = mapped_column(ForeignKey("document_chunks.id"), index=True)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    vector_id: Mapped[str] = mapped_column(String(120), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    title: Mapped[str | None] = mapped_column(String(240))


class Message(TimestampMixin, Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class QueryRun(TimestampMixin, Base):
    __tablename__ = "query_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"))
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    route: Mapped[str] = mapped_column(String(80), nullable=False)
    mode: Mapped[str] = mapped_column(String(40), nullable=False)
    cache_status: Mapped[str] = mapped_column(String(40), default="miss")


class RetrievalCandidate(TimestampMixin, Base):
    __tablename__ = "retrieval_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    query_run_id: Mapped[str] = mapped_column(ForeignKey("query_runs.id"), index=True)
    chunk_id: Mapped[str] = mapped_column(ForeignKey("document_chunks.id"), index=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[str] = mapped_column(String(80), nullable=False)


class CitedEvidence(TimestampMixin, Base):
    __tablename__ = "cited_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    query_run_id: Mapped[str] = mapped_column(ForeignKey("query_runs.id"), index=True)
    chunk_id: Mapped[str | None] = mapped_column(ForeignKey("document_chunks.id"))
    citation_label: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(40), nullable=False)


class GeneratedAnswer(TimestampMixin, Base):
    __tablename__ = "generated_answers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    query_run_id: Mapped[str] = mapped_column(ForeignKey("query_runs.id"), index=True)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_label: Mapped[str] = mapped_column(String(40), nullable=False)
    refusal_reason: Mapped[str | None] = mapped_column(Text)
    live_grounding_used: Mapped[bool] = mapped_column(default=False)


class VerificationResult(TimestampMixin, Base):
    __tablename__ = "verification_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    query_run_id: Mapped[str] = mapped_column(ForeignKey("query_runs.id"), index=True)
    citation_valid: Mapped[bool] = mapped_column(default=False)
    unsupported_claim_count: Mapped[int] = mapped_column(Integer, default=0)
    contradiction_count: Mapped[int] = mapped_column(Integer, default=0)
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class CacheEntryMetadata(TimestampMixin, Base):
    __tablename__ = "cache_entry_metadata"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    cache_key: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    cache_type: Mapped[str] = mapped_column(String(60), nullable=False)
    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False)


class EvaluationCase(TimestampMixin, Base):
    __tablename__ = "evaluation_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    input_query: Mapped[str] = mapped_column(Text, nullable=False)
    expected_behavior: Mapped[str] = mapped_column(Text, nullable=False)


class EvaluationRun(TimestampMixin, Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    summary: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class LatencyMetric(TimestampMixin, Base):
    __tablename__ = "latency_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    query_run_id: Mapped[str | None] = mapped_column(ForeignKey("query_runs.id"))
    metric_name: Mapped[str] = mapped_column(String(120), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
