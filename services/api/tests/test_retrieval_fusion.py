from app.retrieval.fusion import RankedCandidate, fuse_ranked_candidates


def test_rrf_fusion_prefers_candidates_supported_by_multiple_sources() -> None:
    fused = fuse_ranked_candidates(
        dense=[
            RankedCandidate(chunk_id="dense-only", source="dense", rank=1, score=1.0),
            RankedCandidate(chunk_id="both", source="dense", rank=2, score=0.9),
        ],
        keyword=[
            RankedCandidate(chunk_id="both", source="keyword", rank=1, score=3.0),
            RankedCandidate(chunk_id="keyword-only", source="keyword", rank=2, score=2.0),
        ],
        limit=3,
    )

    assert [candidate.chunk_id for candidate in fused] == [
        "both",
        "dense-only",
        "keyword-only",
    ]
    assert fused[0].source == "hybrid"


def test_rrf_fusion_respects_limit() -> None:
    fused = fuse_ranked_candidates(
        dense=[
            RankedCandidate(chunk_id=f"dense-{index}", source="dense", rank=index, score=1.0)
            for index in range(1, 5)
        ],
        keyword=[],
        limit=2,
    )

    assert [candidate.chunk_id for candidate in fused] == ["dense-1", "dense-2"]
