from math import ceil

from pydantic import BaseModel, Field


class EvaluationCaseResult(BaseModel):
    case_id: str
    category: str
    retrieval_hit: bool
    citation_valid: bool
    refusal_correct: bool
    contradiction_correct: bool
    latency_ms: int = Field(ge=0)
    cache_hit: bool
    secret_leak_count: int = Field(ge=0)


class EvaluationSummary(BaseModel):
    case_count: int
    retrieval_hit_rate: float
    citation_validity_rate: float
    refusal_correctness_rate: float
    contradiction_correctness_rate: float
    latency_p50_ms: int
    latency_p95_ms: int
    cache_hit_rate: float
    secret_leak_count: int


def summarize_evaluation_results(
    results: list[EvaluationCaseResult],
) -> EvaluationSummary:
    if not results:
        return EvaluationSummary(
            case_count=0,
            retrieval_hit_rate=0.0,
            citation_validity_rate=0.0,
            refusal_correctness_rate=0.0,
            contradiction_correctness_rate=0.0,
            latency_p50_ms=0,
            latency_p95_ms=0,
            cache_hit_rate=0.0,
            secret_leak_count=0,
        )

    return EvaluationSummary(
        case_count=len(results),
        retrieval_hit_rate=_rate([result.retrieval_hit for result in results]),
        citation_validity_rate=_rate([result.citation_valid for result in results]),
        refusal_correctness_rate=_rate([result.refusal_correct for result in results]),
        contradiction_correctness_rate=_rate([result.contradiction_correct for result in results]),
        latency_p50_ms=_percentile([result.latency_ms for result in results], 0.50),
        latency_p95_ms=_percentile([result.latency_ms for result in results], 0.95),
        cache_hit_rate=_rate([result.cache_hit for result in results]),
        secret_leak_count=sum(result.secret_leak_count for result in results),
    )


def _rate(values: list[bool]) -> float:
    return sum(1 for value in values if value) / len(values)


def _percentile(values: list[int], percentile: float) -> int:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, ceil(len(ordered) * percentile) - 1))
    return ordered[index]
