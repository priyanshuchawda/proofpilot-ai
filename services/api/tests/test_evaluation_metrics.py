from app.evaluation.metrics import EvaluationCaseResult, summarize_evaluation_results


def test_summarize_evaluation_results_computes_deterministic_metrics() -> None:
    summary = summarize_evaluation_results(
        [
            EvaluationCaseResult(
                case_id="answerable-1",
                category="answerable",
                retrieval_hit=True,
                citation_valid=True,
                refusal_correct=True,
                contradiction_correct=True,
                latency_ms=100,
                cache_hit=False,
                secret_leak_count=0,
            ),
            EvaluationCaseResult(
                case_id="no-answer-1",
                category="no-answer",
                retrieval_hit=False,
                citation_valid=True,
                refusal_correct=True,
                contradiction_correct=True,
                latency_ms=300,
                cache_hit=True,
                secret_leak_count=0,
            ),
        ]
    )

    assert summary.case_count == 2
    assert summary.retrieval_hit_rate == 0.5
    assert summary.citation_validity_rate == 1.0
    assert summary.refusal_correctness_rate == 1.0
    assert summary.contradiction_correctness_rate == 1.0
    assert summary.latency_p50_ms == 100
    assert summary.latency_p95_ms == 300
    assert summary.cache_hit_rate == 0.5
    assert summary.secret_leak_count == 0
