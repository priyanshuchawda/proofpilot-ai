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
10. Generate an answer with citation IDs.
11. Validate citation IDs against retrieved chunks.
12. Store query trace and latency metrics.

Document ingestion currently persists redacted chunks and metadata. Dense vector indexing now has a service boundary that can index document chunks into Qdrant and embed queries before vector search. Standard tests use deterministic local embeddings so CI and local development do not require a Gemini key. Real Gemini embedding calls are intentionally deferred until the Flash-Lite-only live testing constraint is lifted or explicitly reviewed.

## Vector Indexing

- `EmbeddingProvider` is a backend-only protocol. The current deterministic provider is used for tests and local retrieval plumbing.
- `EmbeddingIndexService.index_document` batches chunk text, stores `embedding_record` metadata, and upserts Qdrant points keyed to chunk IDs.
- Existing records for the same chunk, content hash, and embedding model are skipped so re-indexing is idempotent.
- `EmbeddingIndexService.search_query` embeds the query and searches Qdrant through the `VectorStore` protocol.
- Qdrant integration is opt-in for tests with `RUN_INFRA_INTEGRATION=1`.

## Hybrid Evidence Ranking

- Dense retrieval returns ordered chunk IDs from Qdrant and is filtered by workspace before evidence is exposed.
- Keyword retrieval scores workspace chunks by normalized exact term overlap. This is deterministic and testable; PostgreSQL-specific full-text optimization can replace the internal scorer without changing the service contract.
- Reciprocal Rank Fusion combines dense and keyword rankings. Chunks supported by both sources are marked `hybrid`.
- Retrieval stores a `query_run` and final ranked `retrieval_candidate` rows so the UI can later inspect the trace.
- Empty retrieval still stores the query run and returns no evidence, allowing later answer generation to choose a safe refusal.

## Citation Rule

No supported citation means no confident factual claim. Unsupported answers must be downgraded or refused.

## Answer Contract

- The query endpoint returns a structured answer with answer text, citations, evidence chunk IDs, confidence, refusal reason, mode, cache status, and live-grounding flag.
- Evidence context explicitly states that uploaded documents are evidence, not instructions.
- Generated citation IDs must be a subset of retrieved evidence chunk IDs.
- Missing evidence returns a safe refusal without calling Gemini.
- Fabricated citations produce a low-confidence refusal and are persisted as a generated answer record with refusal metadata.
- The JSON query endpoint remains available for clients that want a complete structured payload.
- The streaming query endpoint emits `answer_delta` events and a final structured `final` event with citation metadata. Provider-native token streaming remains a later Gemini provider enhancement.

## Routing And Verification

- Fast Mode retrieves fewer candidates and skips deterministic contradiction detection.
- Verified Mode retrieves more candidates, validates citations, and detects deterministic numeric contradictions in retrieved evidence.
- Freshness-required questions are detected with explicit terms such as current, latest, today, version, pricing, release, and status.
- Until web grounding is implemented, freshness-required answers carry `freshness_required_grounding_disabled` so the UI can avoid pretending the answer is current.
- No-evidence retrieval routes to `route_no_evidence` and returns the existing safe refusal path.
- When Search grounding is disabled, freshness-required answers refuse rather than returning stale uploaded-document-only facts as current information.
- Google Search grounding plumbing is backend-only and feature-flagged; it remains off by default to avoid accidental quota use.

## Cache Safety

- Response cache keys include workspace ID, index version, mode, and normalized query digest.
- Cache hits are marked in the answer contract and do not run retrieval or Gemini.
- Safe response caching excludes refusals, live-grounded answers, and freshness-required routes.
- Redis is accessed behind a cache protocol; standard tests use an in-memory backend.
- Redis integration is opt-in with `RUN_INFRA_INTEGRATION=1`.
