# Evaluation Plan

## Dataset Categories

- Answerable document questions.
- No-answer questions.
- Conflicting-document questions.
- Freshness-required questions.
- Prompt-injection document questions.
- Citation-required questions.

## Deterministic Metrics

- Retrieval hit rate.
- Citation ID validity.
- No-evidence refusal correctness.
- Contradiction detection correctness.
- Secret leakage count, target zero.
- Cache hit behavior.
- Latency p50 and p95.

## Reporting

Evaluation runs write reproducible local reports under `evals/results/`. AI quality labels must be clearly separated from deterministic checks and human review.
