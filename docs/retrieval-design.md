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

Document ingestion currently persists redacted chunks and metadata. Dense embeddings and Qdrant indexing are the next retrieval milestone.

## Citation Rule

No supported citation means no confident factual claim. Unsupported answers must be downgraded or refused.
