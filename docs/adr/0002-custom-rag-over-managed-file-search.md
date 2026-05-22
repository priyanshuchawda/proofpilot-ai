# ADR 0002: Custom RAG Over Managed File Search

## Status

Accepted

## Context

The project must demonstrate retrieval architecture, evidence ranking, traceability, citation validation, and local-first infrastructure.

## Decision

Implement custom RAG with PostgreSQL keyword retrieval, Qdrant dense retrieval, deterministic fusion, and local metadata storage. Do not use provider-managed File Search as the primary MVP path.

## Consequences

- Retrieval behavior is inspectable and testable.
- Free-tier risk is lower because indexing infrastructure is local.
- Managed File Search can be revisited later behind a disabled experimental adapter.
