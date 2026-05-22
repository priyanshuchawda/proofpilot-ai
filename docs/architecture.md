# Architecture

ProofPilot AI is a monorepo with a TypeScript frontend, Python AI backend, and local infrastructure.

## Components

- `apps/web`: Next.js App Router UI.
- `services/api`: FastAPI API, retrieval orchestration, Gemini provider boundary, evaluation APIs.
- `services/worker`: planned background ingestion and indexing worker.
- `packages/generated-api-client`: planned generated TypeScript client from FastAPI OpenAPI.
- `infra/docker-compose.yml`: local PostgreSQL, Redis, and Qdrant.

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
