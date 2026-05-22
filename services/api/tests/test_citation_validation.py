from app.answers.citations import validate_citation_ids


def test_validate_citation_ids_accepts_retrieved_evidence_ids() -> None:
    assert validate_citation_ids(
        cited_chunk_ids=["chunk-a", "chunk-b"],
        evidence_chunk_ids={"chunk-a", "chunk-b", "chunk-c"},
    )


def test_validate_citation_ids_rejects_fabricated_ids() -> None:
    assert not validate_citation_ids(
        cited_chunk_ids=["chunk-a", "fabricated"],
        evidence_chunk_ids={"chunk-a", "chunk-b"},
    )
