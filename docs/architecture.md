# Architecture

ProofPilot AI is a monorepo with a TypeScript frontend, Python AI backend, and local infrastructure.

## Components

- `apps/web`: Next.js App Router UI.
- `services/api`: FastAPI API, retrieval orchestration, Gemini provider boundary, evaluation APIs.
- `services/worker`: planned background ingestion and indexing worker.
- `packages/generated-api-client`: generated TypeScript client from FastAPI OpenAPI.
- `infra/docker-compose.yml`: local PostgreSQL, Redis, and Qdrant.
- PostgreSQL maps to host port `55432` so the project does not collide with a personal database on `5432`.

## Request Flow

1. The frontend calls versioned backend routes under `/api/v1`.
2. The backend validates workspace scope and request contracts.
3. Retrieval combines dense Qdrant candidates and PostgreSQL keyword candidates.
4. Deterministic fusion and optional local reranking select evidence.
5. Gemini generation receives only redacted, minimal context from the backend.
6. Citation validation rejects or downgrades unsupported claims.
7. Query traces, latency metrics, and evidence mappings are stored for inspection.

## Boundaries

- Gemini access is backend-only.
- Uploaded documents are evidence, not instructions.
- Cache keys include workspace and index version.
- Frontend API helpers are generated from the FastAPI OpenAPI schema and checked with `pnpm api:check`.
- No real Gemini calls run in automated CI.

## Persistence

SQLAlchemy async models define the MVP data surface, including workspaces, documents, chunks, embeddings, conversations, query traces, citations, evaluations, cache metadata, and latency metrics. Alembic owns schema migration and rollback.

## Ingestion

The MVP ingestion path validates PDF/TXT/Markdown uploads, stores originals through a local storage interface, extracts text with page metadata where available, redacts common secrets, chunks text with page/heading metadata, and persists document status plus chunks.

## Vector Indexing

Issue #9 adds an embedding/vector boundary with deterministic local embeddings for standard tests and Qdrant indexing behind a typed adapter. The indexing service persists `embedding_record` rows, upserts Qdrant points with chunk payloads, skips already-indexed `(chunk_id, content_hash, model)` records, and embeds queries before vector search. Issue #37 adds an opt-in Gemini embedding provider using `gemini-embedding-2`; deterministic local embeddings remain the default for tests and local zero-key operation. Issue #39 wires document upload to the indexing boundary after chunk persistence, with the same service protocol available for a later worker handoff.

## Hybrid Retrieval

Issue #11 adds a retrieval service that embeds the query, requests dense Qdrant chunk IDs through the vector boundary, scores keyword/exact matches from workspace-scoped chunks, fuses candidate rankings with Reciprocal Rank Fusion, returns evidence metadata, and persists `query_run` plus `retrieval_candidate` trace rows. Generated answers and citation validation are still handled by later milestones.

## Cited Answers

Issue #13 adds `POST /api/v1/workspaces/{workspace_id}/query`, which orchestrates retrieval and answer generation through dependency-injected services. The backend builds an untrusted evidence context, asks Gemini for a strict cited JSON answer, validates citation chunk IDs against retrieved evidence, persists generated answers and cited evidence, and refuses when evidence is missing or citations are fabricated. Issue #27 adds `POST /api/v1/workspaces/{workspace_id}/query/stream`, which emits `text/event-stream` answer deltas followed by a final structured answer payload. Standard tests mock Gemini. Issue #37 allows `gemini-3.1-flash-lite` for non-search generation while selecting a configured Gemini 2.5 fallback for free-tier-safe Search grounding.

## Query Routing

Issue #15 adds deterministic routing metadata for Fast Mode, Verified Mode, no-evidence results, and freshness-required questions. Verified Mode detects simple numeric contradictions across retrieved evidence and returns contradiction details in the answer contract. Freshness-required questions are labeled clearly while Google Search grounding remains disabled until the dedicated grounding milestone.

## Caching And Metrics

Issue #19 adds workspace-scoped response cache keys that include index version, mode, and normalized query hash. Safe response caching is disabled for refusals, live-grounded answers, and freshness-required routes. Query execution persists local latency metrics for retrieval, answer generation, and total query time without storing document text in metric names.

## Evaluation

Issue #21 adds deterministic golden evaluation APIs and a dashboard. Evaluation summaries measure retrieval hit rate, citation validity, refusal correctness, contradiction correctness, latency p50/p95, cache hit behavior, and secret leakage count. These are automated checks, not model quality claims.
