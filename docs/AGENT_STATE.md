# Agent State

Last updated: 2026-05-23

## Completed Issues

- #1: Repository bootstrap and engineering foundation.

## Current Architecture Decisions

- Build as a monorepo with `apps/web` for Next.js and `services/api` for FastAPI.
- Keep Gemini access backend-only.
- Use local Docker infrastructure for PostgreSQL, Redis, and Qdrant.
- Prefer custom RAG over provider-managed File Search for the MVP so retrieval architecture is visible and testable.
- Treat Gemini model IDs and Google Search grounding as configuration. Search grounding is disabled by default until the selected model is verified as free-tier-safe.
- For current development/live testing, use only `gemini-2.5-flash-lite` for generation routes. Defer Gemini 3.5 model usage until final production-readiness review.
- Keep real Gemini smoke tests manual only behind `RUN_GEMINI_SMOKE=1`.

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

## Unresolved Risks

- Issue #1 is merged.
- GitHub Actions are intentionally disabled for now to avoid spending Actions minutes before final hardening.
- Gemini embedding and File Search pricing details must be rechecked before embedding or managed File Search integration code is added.
- In-app browser automation was unavailable in this session; Playwright was also not installed in the shared Node runtime. Issue 1 used HTTP smoke testing instead.
- Issue #3 PR and merge are still pending.

## Next Issue

- Commit Issue #3, open PR, and merge after local checks/security checks pass.
