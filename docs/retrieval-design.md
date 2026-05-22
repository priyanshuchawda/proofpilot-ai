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

## Citation Rule

No supported citation means no confident factual claim. Unsupported answers must be downgraded or refused.
