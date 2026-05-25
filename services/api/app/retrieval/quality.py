import re
from dataclasses import dataclass, field
from typing import cast

from app.retrieval.fusion import RankedCandidate

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")


@dataclass(frozen=True)
class QualityCandidate:
    candidate: RankedCandidate
    text: str
    details: dict[str, object] = field(default_factory=lambda: {})


def rerank_for_quality(
    *,
    query: str,
    candidates: list[QualityCandidate],
    limit: int,
    minimum_quality_score: float = 0.01,
    redundancy_threshold: float = 0.92,
) -> tuple[list[QualityCandidate], list[QualityCandidate]]:
    query_tokens = _tokens(query)
    scored = [_with_quality_score(item, query_tokens=query_tokens) for item in candidates]
    ordered = sorted(
        scored,
        key=lambda item: (
            -_detail_float(item, "quality_score"),
            item.candidate.rank,
            item.candidate.chunk_id,
        ),
    )

    selected: list[QualityCandidate] = []
    dropped: list[QualityCandidate] = []
    for item in ordered:
        quality_score = _detail_float(item, "quality_score")
        if quality_score < minimum_quality_score:
            dropped.append(_with_detail(item, "dropped_reason", "low_signal"))
            continue
        if any(
            _jaccard(_tokens(item.text), _tokens(existing.text)) >= redundancy_threshold
            for existing in selected
        ):
            dropped.append(_with_detail(item, "dropped_reason", "redundant"))
            continue
        selected.append(item)
        if len(selected) >= limit:
            dropped.extend(
                _with_detail(remaining, "dropped_reason", "outside_limit")
                for remaining in ordered[ordered.index(item) + 1 :]
            )
            break

    return _renumber(selected), dropped


def _with_quality_score(
    item: QualityCandidate,
    *,
    query_tokens: set[str],
) -> QualityCandidate:
    text_tokens = _tokens(item.text)
    overlap = len(query_tokens & text_tokens) / max(1, len(query_tokens))
    exact = bool(query_tokens) and " ".join(query_tokens) in " ".join(text_tokens)
    quality_score = item.candidate.score + (0.05 * overlap) + (0.1 if exact else 0.0)
    reason = "exact_match" if exact or overlap >= 0.8 else "fusion_score"
    return QualityCandidate(
        candidate=item.candidate.model_copy(update={"score": quality_score}),
        text=item.text,
        details={
            **item.details,
            "lexical_overlap": round(overlap, 4),
            "promotion_reason": reason,
            "quality_score": round(quality_score, 8),
        },
    )


def _with_detail(item: QualityCandidate, key: str, value: object) -> QualityCandidate:
    return QualityCandidate(
        candidate=item.candidate,
        text=item.text,
        details={**item.details, key: value},
    )


def _renumber(items: list[QualityCandidate]) -> list[QualityCandidate]:
    return [
        QualityCandidate(
            candidate=item.candidate.model_copy(update={"rank": rank}),
            text=item.text,
            details=item.details,
        )
        for rank, item in enumerate(items, start=1)
    ]


def _tokens(value: str) -> set[str]:
    return set(_TOKEN_PATTERN.findall(value.lower()))


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    return len(left & right) / max(1, len(left | right))


def _detail_float(item: QualityCandidate, key: str) -> float:
    value = item.details[key]
    return cast(float, value)
