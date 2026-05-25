# Evaluation Plan

## Dataset Categories

Golden cases live under `evals/datasets/golden-cases.json`.

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

Evaluation runs write ignored local JSON reports under `evals/results/`. AI quality labels must be clearly separated from deterministic checks and human review.

The MVP evaluation API exposes:

- `POST /api/v1/evaluations/run`
- `GET /api/v1/evaluations/runs/{run_id}`
- `GET /api/v1/metrics/summary`

## Browser Contract Verification

`pnpm e2e` runs a deterministic Playwright flow against the production frontend build. It validates workspace creation, public document upload status progression, Verified Mode SSE rendering, document citation display, and persisted retrieval trace display using controlled API fixtures. This check validates UI orchestration only; it is not counted as Gemini quality, backend persistence, or worker/indexing evidence.

`RUN_FULL_STACK_SMOKE=1 pnpm fullstack:smoke` is an opt-in local integration smoke. It starts Docker-backed PostgreSQL, Redis, and Qdrant; applies migrations; runs the API plus one worker; builds the frontend; uploads a public Markdown document; waits for real worker indexing; asks a Verified Mode question; and verifies cited answer, evidence, and persisted trace rendering. The default path forces the mock Gemini provider and deterministic local embeddings. `RUN_FULL_STACK_GEMINI_LIVE=1` is reserved for an explicit live-provider variant.
