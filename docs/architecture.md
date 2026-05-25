# Architecture

ProofPilot AI is a monorepo with a TypeScript frontend, Python AI backend, and local infrastructure.

## Components

- `apps/web`: Next.js App Router UI.
- `services/api`: FastAPI API, retrieval orchestration, Gemini provider boundary, evaluation APIs.
- `services/worker`: worker runbook; the MVP executable is shared from `services/api/app/ingestion/worker.py`.
- `packages/generated-api-client`: generated TypeScript client from FastAPI OpenAPI.
- `infra/docker-compose.yml`: local PostgreSQL, Redis, and Qdrant.
- PostgreSQL maps to host port `55432` so the project does not collide with a personal database on `5432`.

## Request Flow

1. The frontend calls versioned backend routes under `/api/v1`.
2. The backend validates workspace scope and request contracts.
3. Retrieval combines dense Qdrant candidates and PostgreSQL keyword candidates.
4. Deterministic fusion and optional local reranking select evidence.
5. Gemini generation receives only redacted, minimal context from the backend.
6. Citation validation rejects or downgrades unsupported document claims and un-attributed live-web answers.
7. Query traces, latency metrics, and evidence mappings are stored for inspection.

## Boundaries

- Gemini access is backend-only.
- Uploaded documents are evidence, not instructions.
- Cache keys include workspace and index version.
- Frontend API helpers are generated from the FastAPI OpenAPI schema and checked with `pnpm api:check`.
- Playwright browser coverage exercises the upload-to-cited-answer UI contract against deterministic versioned API/SSE fixtures; infrastructure and Gemini paths retain separate verification.
- Sensitive POST routes use a Redis-backed fixed-window rate limiter keyed by hashed backend-observed client identifiers. Authenticated principal scoping is deferred to the auth/workspace ownership issue.
- API responses carry `X-Request-ID`, and local structured request logs contain only safe metadata: method, path without query string, status, duration, request ID, rate-limit outcome, and safe query-run correlation fields when available.
- Local workspace ownership is represented by `owner_session_id` on workspaces. `X-ProofPilot-Session` provides a free local identity boundary, and `PROOFPILOT_WORKSPACE_OWNERSHIP_ENABLED=true` enforces cross-session isolation for workspaces, documents, queries, and query-run traces.
- No real Gemini calls run in automated CI.

## Persistence

SQLAlchemy async models define the MVP data surface, including workspaces, documents, chunks, embeddings, conversations, query traces, citations, evaluations, cache metadata, and latency metrics. Alembic owns schema migration and rollback.

## Ingestion

The MVP ingestion path validates PDF/TXT/Markdown uploads and stores originals through a local storage interface in the HTTP request. It then places the document ID on a local Redis pending queue and returns `uploaded`. The Python worker reserves a job into an in-flight list, extracts text with page metadata where available, redacts common secrets, chunks and indexes evidence, advances persisted statuses through `parsed`, `chunked`, `embedded`, `indexed`, and `ready`, and acknowledges terminal processing. Startup recovers unacknowledged in-flight items; this local recovery contract assumes one worker process. Failed processing records a non-sensitive `failed` status that the UI surfaces.

## Vector Indexing

Issue #9 adds an embedding/vector boundary with deterministic local embeddings for standard tests and Qdrant indexing behind a typed adapter. The indexing service persists `embedding_record` rows, upserts Qdrant points with chunk payloads, skips already-indexed `(chunk_id, content_hash, model)` records, and embeds queries before vector search. Issue #37 adds an opt-in Gemini embedding provider using `gemini-embedding-2`; deterministic local embeddings remain the default for tests and local zero-key operation. Issue #39 wires document processing to the indexing boundary after chunk persistence. Issue #46 makes Qdrant collection setup idempotent for compatible existing vector dimensions and distance metrics. Issue #51 moves processing/indexing behind the queued worker; incompatible vector configuration now produces the worker's safe `failed` ingestion status instead of failing an upload request.

## Hybrid Retrieval

Issue #11 adds a retrieval service that embeds the query, requests dense Qdrant chunk IDs through the vector boundary, fuses candidate rankings with Reciprocal Rank Fusion, returns evidence metadata, and persists `query_run` plus `retrieval_candidate` trace rows. Issue #49 moves production keyword retrieval to workspace-scoped PostgreSQL full-text ranking over chunk headings and content, protected by a GIN expression index; SQLite unit tests inject deterministic term scoring through the same retriever protocol. Issue #61 adds deterministic post-fusion quality controls for exact-match boosting, low-signal filtering, redundancy suppression, and persisted candidate `details`.

## Cited Answers

Issue #13 adds `POST /api/v1/workspaces/{workspace_id}/query`, which orchestrates retrieval and answer generation through dependency-injected services. The backend builds an untrusted evidence context, asks Gemini for a strict cited JSON answer, validates citation chunk IDs against retrieved evidence, persists generated answers and cited evidence, and refuses when evidence is missing or citations are fabricated. Issue #27 adds `POST /api/v1/workspaces/{workspace_id}/query/stream`, which emits `text/event-stream` answer deltas followed by a final structured answer payload. Standard tests mock Gemini. Issue #37 allows `gemini-3.1-flash-lite` for non-search generation while selecting a configured Gemini 2.5 fallback for free-tier-safe Search grounding. Issue #41 consumes Gemini Search grounding metadata, inserts inline `[web-n]` markers from supported text spans, returns only web sources referenced by those support spans distinctly from document chunks, and exposes required Search Suggestions content through an isolated UI iframe. Issue #45 retries an ordinary, non-Search generation request once through the configured lightweight model only after temporary provider unavailability, and exposes the successful model in the response trace.

Issue #62 strengthens document answer validation with paragraph-level citation coverage. The MVP keeps provider-native Gemini streaming disabled and streams only validated final answer text over backend SSE, preserving the evidence-first contract.

## Query Routing

Issue #15 adds deterministic routing metadata for Fast Mode, Verified Mode, no-evidence results, and freshness-required questions. Verified Mode detects simple numeric contradictions across retrieved evidence and returns contradiction details in the answer contract. Issue #41 makes freshness routing precede empty-document refusal, allowing a current-information question with no uploaded source to use Google Search only when the feature flag is explicitly enabled. Search responses without sources, inline mappings, or required Search Suggestions are refused. Gemini quota exhaustion produces an explicit retry-later refusal. Temporary ordinary-generation overload may use the configured free-tier fallback once; Search remains on its separately verified Search-safe model path and no paid fallback is reachable.

## Caching And Metrics

Issue #19 adds workspace-scoped response cache keys that include index version, mode, and normalized query hash. Safe response caching is disabled for refusals, live-grounded answers, and freshness-required routes. Query execution persists local latency metrics for retrieval, answer generation, and total query time without storing document text in metric names.

Issue #58 adds request-scoped JSON logging through middleware. The middleware propagates valid `X-Request-ID` values or generates one, exposes the header to browsers, and logs only trace-safe fields. Query handlers attach safe answer metadata to the request state so logs can correlate client-visible failures or slow responses with `query_run_id`, cache status, effective generation model, and live-grounding usage. It intentionally excludes request bodies, uploaded document text, raw headers, query strings, and secrets.

Issue #65 adds local operational counters for Gemini requests, Gemini availability errors, and response-cache hit/miss outcomes. Counters are in-process and aggregate-only: they label Gemini calls by provider/model/Search usage, cache outcomes by cache name/mode/hashed workspace ID, and never include prompts, uploaded document text, raw workspace IDs, headers, or API keys. `GET /api/v1/metrics/operational` returns those counters with the existing safe dependency health snapshot.

Issue #71 surfaces the same safe operational snapshot in the dashboard so local testing can confirm dependency health, provider activity, provider errors, and cache behavior without exposing private inputs.

## Abuse Controls

Issue #57 protects document upload, query, streamed query, and evaluation execution with configurable Redis-backed fixed-window limits. Rate-limit keys hash the backend-observed client identifier before storage, exceeded budgets return HTTP `429` with `Retry-After`, and Redis failures fail closed with a safe `503` for protected expensive actions. Until authentication exists, client network address is the MVP caller boundary.

## Evaluation

Issue #21 adds deterministic golden evaluation APIs and a dashboard. Evaluation summaries measure retrieval hit rate, citation validity, refusal correctness, contradiction correctness, latency p50/p95, cache hit behavior, and secret leakage count. These are automated checks, not model quality claims.
