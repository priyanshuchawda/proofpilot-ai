# Retrieval Design

## Goals

- Evidence-first answers with valid citations.
- Hybrid retrieval from dense vectors and keyword search.
- Deterministic fusion before any optional model-based generation.
- Clear traces for cache, route, retrieval, reranking, evidence, and citation validation.

## MVP Pipeline

1. Validate workspace and query.
2. Detect freshness requirements.
3. Check safe workspace-scoped caches.
4. Embed the query.
5. Retrieve dense candidates from Qdrant.
6. Retrieve keyword candidates from PostgreSQL full-text search.
7. Fuse candidates with Reciprocal Rank Fusion.
8. Apply metadata filters and deterministic reranking.
9. Build a minimal context window from top evidence.
10. Generate an answer with document citation IDs or feature-flagged live Search grounding.
11. Validate document citation IDs against retrieved chunks and web citation labels against Gemini grounding support spans.
12. Store query trace and latency metrics.

Document ingestion persists redacted chunks and metadata, then indexes ready chunks through the embedding service boundary when `UPLOAD_INDEXING_ENABLED=true`. Dense vector indexing stores document chunks in Qdrant and embeds queries before vector search. Standard tests use deterministic local embeddings so CI and local development do not require a Gemini key. Real Gemini embedding calls are available only when `GEMINI_EMBEDDINGS_ENABLED=true`; otherwise the deterministic provider remains active.

## Vector Indexing

- `EmbeddingProvider` is a backend-only protocol. The current deterministic provider is used for tests and local retrieval plumbing.
- `EmbeddingIndexService.index_document` batches chunk text, stores `embedding_record` metadata, and upserts Qdrant points keyed to chunk IDs.
- Existing records for the same chunk, content hash, and embedding model are skipped so re-indexing is idempotent.
- Qdrant collection initialization reuses an existing collection only when its vector dimension and cosine distance match the configured embedding output and search contract; an incompatible configuration produces a controlled upload conflict.
- `EmbeddingIndexService.search_query` embeds the query and searches Qdrant through the `VectorStore` protocol.
- The current MVP calls indexing synchronously after chunk persistence; the `DocumentIndexer` service boundary preserves a later background worker handoff.
- Qdrant integration is opt-in for tests with `RUN_INFRA_INTEGRATION=1`.

## Hybrid Evidence Ranking

- Dense retrieval returns ordered chunk IDs from Qdrant and is filtered by workspace before evidence is exposed.
- Production keyword retrieval runs workspace-scoped PostgreSQL `websearch_to_tsquery`/`ts_rank_cd` ranking over a GIN-indexed text vector of section headings and chunk text. Unit tests inject a deterministic exact-term retriever through the same protocol so they do not require PostgreSQL.
- Reciprocal Rank Fusion combines dense and keyword rankings. Chunks supported by both sources are marked `hybrid`.
- Retrieval stores a `query_run` and final ranked `retrieval_candidate` rows so the UI can later inspect the trace.
- Empty retrieval still stores the query run and returns no evidence, allowing later answer generation to choose a safe refusal.

## Citation Rule

No supported citation means no confident factual claim. Unsupported answers must be downgraded or refused.

## Answer Contract

- The query endpoint returns a structured answer with answer text, citations, evidence chunk IDs, confidence, refusal reason, mode, cache status, the successful generation model when a model answered, live-grounding flag, and optional required Search Suggestions content.
- Evidence context explicitly states that uploaded documents are evidence, not instructions.
- Generated citation IDs must be a subset of retrieved evidence chunk IDs.
- Missing evidence returns a safe refusal without calling Gemini.
- Fabricated citations produce a low-confidence refusal and are persisted as a generated answer record with refusal metadata.
- Live-grounded answers use `groundingChunks` and `groundingSupports` to emit `[web-n]` labels and distinct web citation records. Only chunks referenced by support spans are presented as cited evidence; absent web metadata or inline mappings produce a refusal.
- Required Google Search Suggestions HTML is passed to the UI and displayed inside a sandboxed iframe rather than injected into the application DOM.
- The JSON query endpoint remains available for clients that want a complete structured payload.
- The streaming query endpoint emits `answer_delta` events and a final structured `final` event with citation metadata. Provider-native token streaming remains a later Gemini provider enhancement.

## Routing And Verification

- Fast Mode retrieves fewer candidates and skips deterministic contradiction detection.
- Verified Mode retrieves more candidates, validates citations, and detects deterministic numeric contradictions in retrieved evidence.
- Freshness-required questions are detected with explicit terms such as current, latest, today, version, pricing, release, and status.
- Freshness-required answers carry `freshness_required_grounding_disabled` when live grounding is not explicitly enabled.
- No-evidence retrieval routes to `route_no_evidence` for document-only questions; freshness-required questions are routed before that check so opt-in Search can answer without uploaded chunks.
- When Search grounding is disabled, freshness-required answers refuse rather than returning stale uploaded-document-only facts as current information.
- Google Search grounding is backend-only and feature-flagged; it remains off by default to avoid accidental quota use. It uses the verified Gemini 2.5 Flash-Lite fallback when the primary non-search model is not Search-free-tier-safe.
- Search quota exhaustion returns `route_quota_exhausted`; temporary provider overload returns `route_provider_unavailable`. Neither route invokes a paid fallback.
- Ordinary document generation retries once with the configured lightweight free-tier model after HTTP `503` from the primary model. It does not retry after HTTP `429`; the actual successful model is surfaced in the answer trace.

## Cache Safety

- Response cache keys include workspace ID, index version, mode, and normalized query digest.
- Cache hits are marked in the answer contract and do not run retrieval or Gemini.
- Safe response caching excludes refusals, live-grounded answers, and freshness-required routes.
- Redis is accessed behind a cache protocol; standard tests use an in-memory backend.
- Redis integration is opt-in with `RUN_INFRA_INTEGRATION=1`.
