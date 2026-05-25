from app.retrieval.fusion import RankedCandidate
from app.retrieval.quality import QualityCandidate, rerank_for_quality


def test_quality_rerank_promotes_exact_match_over_dense_only_candidate() -> None:
    selected, dropped = rerank_for_quality(
        query="pricing release notes",
        candidates=[
            QualityCandidate(
                candidate=RankedCandidate(chunk_id="dense", source="dense", rank=1, score=0.05),
                text="Architecture overview without the requested terms.",
            ),
            QualityCandidate(
                candidate=RankedCandidate(chunk_id="exact", source="keyword", rank=2, score=0.02),
                text="The pricing release notes require review.",
            ),
        ],
        limit=2,
    )

    assert [item.candidate.chunk_id for item in selected] == ["exact", "dense"]
    assert selected[0].details["promotion_reason"] == "exact_match"
    assert dropped == []


def test_quality_rerank_drops_redundant_chunks_for_diversity() -> None:
    selected, dropped = rerank_for_quality(
        query="rollout evidence approval",
        candidates=[
            QualityCandidate(
                candidate=RankedCandidate(chunk_id="a", source="hybrid", rank=1, score=0.08),
                text="The rollout evidence is required before approval.",
            ),
            QualityCandidate(
                candidate=RankedCandidate(chunk_id="b", source="hybrid", rank=2, score=0.07),
                text="The rollout evidence is required before approval.",
            ),
            QualityCandidate(
                candidate=RankedCandidate(chunk_id="c", source="keyword", rank=3, score=0.03),
                text="The owner is ProofPilot QA.",
            ),
        ],
        limit=3,
    )

    assert [item.candidate.chunk_id for item in selected] == ["a", "c"]
    assert [item.candidate.chunk_id for item in dropped] == ["b"]
    assert dropped[0].details["dropped_reason"] == "redundant"


def test_quality_rerank_drops_low_signal_candidates() -> None:
    selected, dropped = rerank_for_quality(
        query="quota grounding fallback",
        candidates=[
            QualityCandidate(
                candidate=RankedCandidate(chunk_id="noise", source="dense", rank=1, score=0.001),
                text="Completely unrelated content.",
            )
        ],
        limit=3,
        minimum_quality_score=0.02,
    )

    assert selected == []
    assert dropped[0].details["dropped_reason"] == "low_signal"
