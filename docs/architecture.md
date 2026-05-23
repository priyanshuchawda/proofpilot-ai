# Architecture

ProofPilot AI is a monorepo with a TypeScript frontend, Python AI backend, and local infrastructure.

## Components

- `apps/web`: Next.js App Router UI.
- `services/api`: FastAPI API, retrieval orchestration, Gemini provider boundary, evaluation APIs.
- `services/worker`: planned background ingestion and indexing worker.
- `packages/generated-api-client`: planned generated TypeScript client from FastAPI OpenAPI.
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
- No real Gemini calls run in automated CI.

## Persistence

SQLAlchemy async models define the MVP data surface, including workspaces, documents, chunks, embeddings, conversations, query traces, citations, evaluations, cache metadata, and latency metrics. Alembic owns schema migration and rollback.

## Ingestion

The MVP ingestion path validates PDF/TXT/Markdown uploads, stores originals through a local storage interface, extracts text with page metadata where available, redacts common secrets, chunks text with page/heading metadata, and persists document status plus chunks.

## Vector Indexing

Issue #9 adds an embedding/vector boundary with deterministic local embeddings for standard tests and Qdrant indexing behind a typed adapter. The indexing service persists `embedding_record` rows, upserts Qdrant points with chunk payloads, skips already-indexed `(chunk_id, content_hash, model)` records, and embeds queries before vector search. Real Gemini embedding calls remain deferred while local live testing is constrained to `gemini-2.5-flash-lite` generation only.

## Hybrid Retrieval

Issue #11 adds a retrieval service that embeds the query, requests dense Qdrant chunk IDs through the vector boundary, scores keyword/exact matches from workspace-scoped chunks, fuses candidate rankings with Reciprocal Rank Fusion, returns evidence metadata, and persists `query_run` plus `retrieval_candidate` trace rows. Generated answers and citation validation are still handled by later milestones.

## Cited Answers

Issue #13 adds `POST /api/v1/workspaces/{workspace_id}/query`, which orchestrates retrieval and answer generation through dependency-injected services. The backend builds an untrusted evidence context, asks Gemini for a strict cited JSON answer, validates citation chunk IDs against retrieved evidence, persists generated answers and cited evidence, and refuses when evidence is missing or citations are fabricated. Standard tests mock Gemini; local live testing remains limited to `gemini-2.5-flash-lite`.

## Query Routing

Issue #15 adds deterministic routing metadata for Fast Mode, Verified Mode, no-evidence results, and freshness-required questions. Verified Mode detects simple numeric contradictions across retrieved evidence and returns contradiction details in the answer contract. Freshness-required questions are labeled clearly while Google Search grounding remains disabled until the dedicated grounding milestone.

## Caching And Metrics

Issue #19 adds workspace-scoped response cache keys that include index version, mode, and normalized query hash. Safe response caching is disabled for refusals, live-grounded answers, and freshness-required routes. Query execution persists local latency metrics for retrieval, answer generation, and total query time without storing document text in metric names.
