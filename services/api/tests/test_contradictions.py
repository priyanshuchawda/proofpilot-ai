from app.answers.contradictions import detect_contradictions
from app.retrieval.schemas import EvidenceChunk


def _evidence(chunk_id: str, text: str) -> EvidenceChunk:
    return EvidenceChunk(
        chunk_id=chunk_id,
        workspace_id="workspace-a",
        document_id="document-a",
        document_version_id="version-a",
        source_filename=f"{chunk_id}.md",
        mime_type="text/markdown",
        page_number=None,
        section_heading="Policy",
        chunk_order=0,
        text=text,
        score=0.9,
        source="hybrid",
    )


def test_detect_contradictions_surfaces_conflicting_numeric_claims() -> None:
    contradictions = detect_contradictions(
        [
            _evidence("chunk-a", "The retention period is 30 days."),
            _evidence("chunk-b", "The retention period is 90 days."),
        ]
    )

    assert len(contradictions) == 1
    assert contradictions[0].chunk_ids == ["chunk-a", "chunk-b"]
    assert contradictions[0].claim_key == "retention period"


def test_detect_contradictions_ignores_matching_claims() -> None:
    assert (
        detect_contradictions(
            [
                _evidence("chunk-a", "The retention period is 30 days."),
                _evidence("chunk-b", "Retention period remains 30 days."),
            ]
        )
        == []
    )
