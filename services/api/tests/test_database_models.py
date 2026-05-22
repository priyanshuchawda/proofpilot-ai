from app.db.base import Base


def test_database_metadata_contains_required_mvp_tables() -> None:
    expected_tables = {
        "workspaces",
        "documents",
        "document_versions",
        "ingestion_jobs",
        "document_chunks",
        "embedding_records",
        "conversations",
        "messages",
        "query_runs",
        "retrieval_candidates",
        "cited_evidence",
        "generated_answers",
        "verification_results",
        "cache_entry_metadata",
        "evaluation_cases",
        "evaluation_runs",
        "latency_metrics",
    }

    assert expected_tables.issubset(set(Base.metadata.tables))
