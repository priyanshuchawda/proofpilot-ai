from app.answers.citations import validate_citation_ids, validate_cited_paragraphs


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


def test_validate_cited_paragraphs_requires_each_paragraph_to_have_a_citation() -> None:
    assert validate_cited_paragraphs(
        answer_text=(
            "ProofPilot requires evidence. [chunk-a]\n\n"
            "The trace must be visible. [chunk-b]"
        ),
        cited_chunk_ids=["chunk-a", "chunk-b"],
    )

    assert not validate_cited_paragraphs(
        answer_text="ProofPilot requires evidence. [chunk-a]\n\nThe trace must be visible.",
        cited_chunk_ids=["chunk-a"],
    )
