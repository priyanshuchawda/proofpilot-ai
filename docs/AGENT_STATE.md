# Agent State

Last updated: 2026-05-24

## Completed Issues

- #1: Repository bootstrap and engineering foundation.
- #3: Free-tier contract and Gemini provider boundary.
- #5: Workspace, database and local infrastructure.
- #7: Secure document upload and ingestion pipeline.
- #9: Embeddings and Qdrant vector indexing.
- #11: Hybrid retrieval and evidence ranking.
- #13: Cited answer generation and streaming chat.
- #15: Query routing, modes, and contradiction checks.
- #17: Free-tier-safe current information grounding.
- #19: Redis caching and latency optimization.
- #21: Evaluation harness and observability dashboard.
- #23: Final UX, documentation, and demo readiness.
- #25: Generated API client and local readiness cleanup.
- #27: Streamed query transport.
- #29: Live health card and browser smoke readiness.
- #31: Workspace and document management UI.

## Current Architecture Decisions

- Build as a monorepo with `apps/web` for Next.js and `services/api` for FastAPI.
- Keep Gemini access backend-only.
- Use local Docker infrastructure for PostgreSQL, Redis, and Qdrant.
- Prefer custom RAG over provider-managed File Search for the MVP so retrieval architecture is visible and testable.
- Treat Gemini model IDs and Google Search grounding as configuration. Search grounding is disabled by default until the selected model is verified as free-tier-safe.
- For current development/live testing, use only `gemini-2.5-flash-lite` for generation routes. Defer Gemini 3.5 model usage until final production-readiness review.
- Keep real Gemini smoke tests manual only behind `RUN_GEMINI_SMOKE=1`.
- Use deterministic local embeddings for current vector plumbing and tests. Real Gemini embedding calls are deferred while live testing is constrained to `gemini-2.5-flash-lite`.
- Hybrid retrieval uses deterministic Reciprocal Rank Fusion over dense Qdrant IDs and workspace-scoped keyword/exact matches, with trace rows persisted for inspection.
- Cited answer generation validates generated citation IDs against retrieved evidence and refuses when evidence is missing or citations are fabricated.
- Query routing now labels Fast Mode, Verified Mode, no-evidence, and freshness-required routes. Verified Mode includes deterministic contradiction detection for simple numeric claims.
- Google Search grounding is feature-flagged and disabled by default. Freshness-required questions refuse clearly when grounding is disabled.
- Response caching is workspace-scoped and index-version-scoped. Safe response caching excludes refusals, live-grounded answers, and freshness-required routes.
- Evaluation runs are deterministic local checks and write ignored JSON summaries under `evals/results/`.
- Frontend API helpers are generated from the FastAPI OpenAPI schema under `packages/generated-api-client` and checked with `pnpm api:check`.
- Query UI uses the streamed query route, which emits answer deltas and a final structured cited payload. Provider-native Gemini token streaming remains deferred.
- Frontend local API defaults use `http://127.0.0.1:8000` to avoid Windows `localhost` ambiguity. Override `NEXT_PUBLIC_API_BASE_URL` when port `8000` is already owned by another local project.
- Dashboard workflow now owns selected workspace state and wires workspace/document management into the query console.
- Query UI now includes a retrieval trace panel built from the final structured answer payload. It shows route, cache status, confidence, freshness, live grounding usage, query run ID, evidence chunk IDs, cited chunk IDs, and contradiction keys without exposing hidden chain-of-thought.
- `GET /api/v1/query-runs/{query_run_id}` exposes persisted trace details for a single query run, including ordered retrieval candidates, cited evidence, generated answer, verification result, and latency metrics. The generated frontend client includes `getQueryRun`.
- Final documentation must keep GitHub Actions deferred until explicit final CI enablement.

## Commands That Passed

- `git --version`
- `gh --version`
- `gh auth status`
- `python --version`
- `uv --version`
- `node --version`
- `corepack --version`
- `pnpm --version`
- `docker --version`
- `docker compose version`
- `uv run pytest tests/test_health.py -q` in `services/api` passed with 1 test.
- `pnpm --filter @proofpilot/web test` passed with 1 test.
- `uv run ruff format --check .` in `services/api`
- `uv run ruff check .` in `services/api`
- `uv run pyright` in `services/api`
- `uv run pytest` in `services/api`
- `pnpm lint`
- `pnpm typecheck`
- `pnpm test`
- `pnpm build`
- `pnpm api:check`
- `docker compose -f infra/docker-compose.yml config`
- Local smoke: `GET http://127.0.0.1:8000/api/v1/health`
- Local smoke: `GET http://127.0.0.1:3000` contains `ProofPilot AI` and `API health`
- Issue #3 focused backend tests: `uv run pytest tests/test_ai_settings.py tests/test_gemini_provider.py tests/test_gemini_smoke.py -q`
- Issue #3 focused frontend test: `pnpm --filter @proofpilot/web test`
- Manual Gemini smoke: `RUN_GEMINI_SMOKE=1 uv run pytest tests/test_gemini_smoke.py -q` passed with `gemini-2.5-flash-lite`
- Issue #3 full local gates: backend format, lint, pyright, pytest; frontend lint, typecheck, test, build; Docker Compose config; frontend secret scan; git diff check.
- Issue #5 focused tests: `uv run pytest tests/test_workspace_api.py tests/test_database_models.py tests/test_dependency_health.py -q`
- Issue #5 standard local gates: backend format, lint, pyright, pytest; frontend lint, typecheck, test, build; Docker Compose config; git diff check.
- Issue #5 Docker integration: `RUN_INFRA_INTEGRATION=1 uv run pytest tests/test_infra_integration.py -q` with `DATABASE_URL` on `127.0.0.1:55432`.
- Issue #5 migration verification: `uv run alembic upgrade head`, `uv run alembic downgrade base`, `uv run alembic upgrade head`.
- Issue #7 focused tests: upload validation, redaction, chunking, PDF extraction, and document API tests.
- Issue #7 standard local gates: backend format, lint, pyright, pytest; frontend lint, typecheck, test, build; Docker Compose config; git diff check.
- Issue #9 focused tests: `uv run pytest tests/test_embeddings.py tests/test_embedding_index_service.py tests/test_qdrant_integration.py -q`
- Issue #9 Docker Qdrant integration: `RUN_INFRA_INTEGRATION=1 uv run pytest tests/test_qdrant_integration.py -q`
- Issue #9 standard local gates: backend format, lint, pyright, pytest; frontend lint, typecheck, test, build; Docker Compose config; git diff check.
- Issue #11 focused tests: `uv run pytest tests/test_retrieval_fusion.py tests/test_hybrid_retrieval_service.py -q`
- Issue #11 backend gates: `uv run ruff format --check .`, `uv run ruff check .`, `uv run pyright`, `uv run pytest`.
- Issue #11 standard local gates: backend format, lint, pyright, pytest; frontend lint, typecheck, test, build; Docker Compose config; git diff check.
- Issue #13 focused backend tests: `uv run pytest tests/test_query_api.py tests/test_citation_validation.py tests/test_answer_service.py tests/test_hybrid_retrieval_service.py -q`
- Issue #13 focused frontend test: `pnpm test -- app/query-console.test.tsx`
- Issue #13 backend gates: `uv run ruff format --check .`, `uv run ruff check .`, `uv run pyright`, `uv run pytest`.
- Issue #13 standard local gates: backend format, lint, pyright, pytest; frontend lint, typecheck, test, build; Docker Compose config; git diff check.
- Issue #13 live smoke: real `gemini-2.5-flash-lite` query orchestration returned a valid cited answer with one citation.
- Issue #15 focused tests: `uv run pytest tests/test_query_routing.py tests/test_contradictions.py tests/test_query_service.py -q`
- Issue #15 backend gates: `uv run ruff format --check .`, `uv run ruff check .`, `uv run pyright`, `uv run pytest`.
- Issue #15 standard local gates: backend format, lint, pyright, pytest; frontend lint, typecheck, test, build; Docker Compose config; git diff check.
- Issue #17 focused tests: `uv run pytest tests/test_answer_service.py tests/test_gemini_provider.py -q`
- Issue #17 standard local gates: backend format, lint, pyright, pytest; frontend lint, typecheck, test, build; Docker Compose config; git diff check.
- Issue #19 focused tests: `uv run pytest tests/test_cache_keys.py tests/test_query_cache.py tests/test_redis_cache_integration.py -q`
- Issue #19 Redis integration: `RUN_INFRA_INTEGRATION=1 uv run pytest tests/test_redis_cache_integration.py -q`
- Issue #19 standard local gates: backend format, lint, pyright, pytest; frontend lint, typecheck, test, build; Docker Compose config; git diff check.
- Issue #21 focused backend tests: `uv run pytest tests/test_evaluation_metrics.py tests/test_evaluation_api.py -q`
- Issue #21 focused frontend test: `pnpm test -- app/evaluation-dashboard.test.tsx`
- Issue #21 standard local gates: backend format, lint, pyright, pytest; frontend lint, typecheck, test, build; Docker Compose config; git diff check.
- Issue #23 focused frontend test: `pnpm test -- app/page.test.tsx`
- Issue #23 standard local gates: backend format, lint, pyright, pytest; frontend lint, typecheck, test, build; Docker Compose config; git diff check; secret-pattern scan with only intentional redaction fixture/pattern matches.
- Issue #25 focused RED checks: `pnpm test -- app/api-client.test.ts` failed on unresolved generated client import; `uv run pytest tests/test_generate_api_client.py -q` failed on missing generator.
- Issue #25 focused GREEN checks: `uv run pytest tests/test_generate_api_client.py -q`; `pnpm test -- app/api-client.test.ts`; `pnpm api:check`; `pnpm typecheck`.
- Issue #25 standard local gates: backend format, lint, pyright, pytest; `pnpm api:check`; frontend lint, typecheck, test, build; Docker Compose config.
- Issue #27 focused RED checks: `uv run pytest tests/test_query_api.py -q` failed on missing stream route; `pnpm test -- app/query-console.test.tsx` failed because the UI still called JSON and could not parse SSE.
- Issue #27 focused GREEN checks: `uv run pytest tests/test_query_api.py -q`; `pnpm test -- app/query-console.test.tsx`; `pnpm typecheck`; `pnpm api:check`.
- Issue #27 standard local gates: backend format, lint, pyright, pytest; `pnpm api:check`; frontend lint, typecheck, test, build; Docker Compose config.
- Issue #29 focused RED check: `pnpm test -- app/health-card.test.tsx` failed on missing `HealthCard`.
- Issue #29 focused GREEN checks: `pnpm test -- app/health-card.test.tsx app/page.test.tsx`; `pnpm test -- app/health-card.test.tsx app/page.test.tsx app/query-console.test.tsx app/api-client.test.ts`; `pnpm api:check`; `pnpm typecheck`.
- Issue #29 standard local gates: backend format, lint, pyright, pytest; `pnpm api:check`; frontend lint, typecheck, test, build; Docker Compose config.
- Issue #29 browser smoke: FastAPI health ran on `127.0.0.1:8010` because port `8000` is owned by another local project; Next.js ran on `127.0.0.1:3000` with `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8010`; in-app browser verified `ProofPilot AI`, `API healthy`, `proofpilot-api v0.1.0`, `gemini-2.5-flash-lite only`, and the privacy warning.
- Issue #31 focused RED checks: `pnpm test -- app/workspace-panel.test.tsx` failed on missing `WorkspacePanel`; `pnpm test -- app/query-console.test.tsx` failed because `QueryConsole` did not accept a selected workspace ID.
- Issue #31 focused GREEN checks: `pnpm test -- app/workspace-panel.test.tsx`; `pnpm test -- app/query-console.test.tsx`; `pnpm test -- app/page.test.tsx app/query-console.test.tsx app/workspace-panel.test.tsx`; `pnpm lint`; `pnpm typecheck`.
- Issue #31 standard local gates: backend format, lint, pyright, pytest; `pnpm api:check`; frontend lint, typecheck, test, build; Docker Compose config.
- Issue #31 Docker-backed smoke: Compose PostgreSQL/Redis/Qdrant running; `uv run alembic upgrade head` passed with `DATABASE_URL` pointed to `127.0.0.1:55432`; FastAPI ran on `127.0.0.1:8010`; browser verified workspace UI, created a workspace, API upload stored `proofpilot-smoke-demo.md`, and the refreshed dashboard showed `ready` with `1 chunks`.
- Issue #33 focused RED check: `pnpm test -- app/query-console.test.tsx` failed on missing `Retrieval trace` region.
- Issue #33 focused GREEN check: `pnpm test -- app/query-console.test.tsx` passed with 4 tests.
- Issue #33 standard local gates: backend format, lint, pyright, pytest; `pnpm api:check`; frontend lint, typecheck, test, build; Docker Compose config.
- Issue #33 live browser smoke: with API on `127.0.0.1:8010`, Docker-backed workspace `Smoke 1779556737178`, and live `gemini-2.5-flash-lite`, Verified Mode returned a cited answer and the dashboard showed the retrieval trace with route, cache miss, confidence, freshness, live grounding status, query run, evidence chunk, cited chunk, and contradiction fields.
- Issue #35 focused RED checks: `uv run pytest tests/test_query_runs_api.py -q` failed on missing query-run detail endpoint; `pnpm test -- app/api-client.test.ts` failed on missing `getQueryRun`; `pnpm test -- app/query-console.test.tsx` failed on missing persisted candidate display.
- Issue #35 focused GREEN checks: `uv run pytest tests/test_query_runs_api.py -q`; `pnpm test -- app/api-client.test.ts`; `pnpm api:check`; `pnpm test -- app/query-console.test.tsx app/api-client.test.ts`.
- Issue #35 standard local gates: backend format, lint, pyright, pytest; `pnpm api:check`; frontend lint, typecheck, test, build; Docker Compose config; git diff check; secret-pattern scan with only intentional redaction fixture matches.
- Issue #35 live browser smoke: with Docker-backed API on `127.0.0.1:8010`, Next.js on `127.0.0.1:3000`, and live `gemini-2.5-flash-lite`, the query UI returned a cited answer and the retrieval trace displayed persisted `keyword #1` candidate metadata for `proofpilot-smoke-demo.md` plus answer, retrieval, and total latency metrics.

## Unresolved Risks

- GitHub Actions are intentionally disabled for now to avoid spending Actions minutes before final hardening.
- Gemini embedding and File Search pricing details must be rechecked before real Gemini embedding calls or managed File Search integration code are added.
- In-app browser automation was unavailable in this session; Playwright was also not installed in the shared Node runtime. Issue 1 used HTTP smoke testing instead.
- Local PostgreSQL uses host port `55432` to avoid a personal Postgres conflict on `5432`.
- Issue #11 keyword retrieval currently uses deterministic exact term overlap over workspace chunks. PostgreSQL full-text optimization remains a later internal improvement behind the same service contract.
- Provider-native Gemini token streaming remains a later enhancement. The current stream transport emits deltas from the finalized cited answer text.
- Local `.env` may point `DATABASE_URL` at `localhost:5432`; Docker Compose PostgreSQL is exposed on `127.0.0.1:55432`, so local smoke commands should override `DATABASE_URL` or update the ignored `.env` value.
- Port `8000` is currently owned by an unrelated local `esp32-ai-builder` backend; use `NEXT_PUBLIC_API_BASE_URL` and an alternate backend port for ProofPilot smoke tests when needed.
- Issue #17 adds the backend-only Google Search tool flag, but Search grounding remains disabled by default. Live grounding smoke is deferred until explicitly enabled because it spends free-tier grounding quota.
- Issue #19 cache-hit latency metrics are not persisted because cache hits do not create a query run yet. Cache miss query runs persist retrieval, answer, and total latency metrics.
- Next.js build no longer emits the parent-lockfile workspace-root warning after setting `turbopack.root`. It still emits an upstream `baseline-browser-mapping` staleness warning.

## Next Issue

- Verify current Gemini model, embedding, and Search grounding docs before changing provider defaults or enabling real embedding/search paths.
