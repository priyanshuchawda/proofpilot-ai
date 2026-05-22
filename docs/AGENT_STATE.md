# Agent State

Last updated: 2026-05-23

## Completed Issues

- #1: Repository bootstrap and engineering foundation.
- #3: Free-tier contract and Gemini provider boundary.
- #5: Workspace, database and local infrastructure.
- #7: Secure document upload and ingestion pipeline.
- #9: Embeddings and Qdrant vector indexing.

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

## Unresolved Risks

- GitHub Actions are intentionally disabled for now to avoid spending Actions minutes before final hardening.
- Gemini embedding and File Search pricing details must be rechecked before real Gemini embedding calls or managed File Search integration code are added.
- In-app browser automation was unavailable in this session; Playwright was also not installed in the shared Node runtime. Issue 1 used HTTP smoke testing instead.
- Local PostgreSQL uses host port `55432` to avoid a personal Postgres conflict on `5432`.
- Issue #11 keyword retrieval currently uses deterministic exact term overlap over workspace chunks. PostgreSQL full-text optimization remains a later internal improvement behind the same service contract.

## Next Issue

- Finish Issue #11 PR after local checks/security checks pass.
