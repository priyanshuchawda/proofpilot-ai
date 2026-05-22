# ADR 0001: Monorepo With TypeScript Frontend And Python Backend

## Status

Accepted

## Context

ProofPilot needs a polished frontend and a retrieval-heavy AI backend. A monorepo keeps contracts, docs, CI, and demo setup together.

## Decision

Use `apps/web` for Next.js TypeScript and `services/api` for FastAPI Python. Keep generated clients and shared UI packages under `packages`.

## Consequences

- CI can validate frontend and backend independently.
- OpenAPI generation can keep contracts synchronized.
- Python remains the primary runtime for AI, retrieval, and ingestion.
