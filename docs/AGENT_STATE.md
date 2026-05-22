# Agent State

Last updated: 2026-05-23

## Completed Issues

- None yet.

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

## Unresolved Risks

- Full Issue 1 quality gates still need to run before commit and PR.
- GitHub Actions are intentionally disabled for now to avoid spending Actions minutes before final hardening.
- Gemini embedding and File Search pricing details must be rechecked in Issue 2 before any integration code is added.
- In-app browser automation was unavailable in this session; Playwright was also not installed in the shared Node runtime. Issue 1 used HTTP smoke testing instead.

## Next Issue

- Commit Issue 1, open PR, merge after local gates pass, then start Issue 2.
