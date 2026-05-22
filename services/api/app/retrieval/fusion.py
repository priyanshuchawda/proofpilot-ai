from collections import defaultdict

from pydantic import BaseModel, Field


class RankedCandidate(BaseModel):
    chunk_id: str
    source: str
    rank: int = Field(ge=1)
    score: float


def fuse_ranked_candidates(
    *,
    dense: list[RankedCandidate],
    keyword: list[RankedCandidate],
    limit: int,
    rrf_k: int = 60,
) -> list[RankedCandidate]:
    scores: dict[str, float] = defaultdict(float)
    best_source_rank: dict[str, tuple[int, str]] = {}

    for candidate in [*dense, *keyword]:
        scores[candidate.chunk_id] += 1.0 / (rrf_k + candidate.rank)
        current_best = best_source_rank.get(candidate.chunk_id)
        if current_best is None or candidate.rank < current_best[0]:
            best_source_rank[candidate.chunk_id] = (candidate.rank, candidate.source)

    sorted_items = sorted(
        scores.items(),
        key=lambda item: (-item[1], best_source_rank[item[0]][0], item[0]),
    )

    fused: list[RankedCandidate] = []
    for rank, (chunk_id, score) in enumerate(sorted_items[:limit], start=1):
        source_count = int(any(candidate.chunk_id == chunk_id for candidate in dense)) + int(
            any(candidate.chunk_id == chunk_id for candidate in keyword)
        )
        fused.append(
            RankedCandidate(
                chunk_id=chunk_id,
                source="hybrid" if source_count > 1 else best_source_rank[chunk_id][1],
                rank=rank,
                score=score,
            )
        )
    return fused
