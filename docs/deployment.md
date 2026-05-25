# Deployment

The MVP is local-first. No paid hosted services are required.

## Local Services

```powershell
docker compose -f infra/docker-compose.yml up -d
```

PostgreSQL is available at `postgresql+asyncpg://proofpilot:proofpilot@127.0.0.1:55432/proofpilot`.
Redis is available at `redis://localhost:6379/0`.
Qdrant is available at `http://localhost:6333`.

## Backend

```powershell
cd services/api
uv run uvicorn app.main:app --reload
```

Apply migrations:

```powershell
cd services/api
uv run alembic upgrade head
```

## Ingestion Worker

Run one local worker from the backend directory in a separate terminal:

```powershell
cd services/api
uv run python -m app.ingestion.worker
```

The worker uses Redis to reserve uploaded documents, persists ingestion progress, and recovers unacknowledged work on restart. The local MVP supports one active worker process.

## Frontend

```powershell
pnpm --filter @proofpilot/web dev
```

Deployment to hosted platforms is deferred until the free-tier contract and secret-handling controls are complete.

## Current Constraints

- GitHub Actions are intentionally deferred until final hardening.
- Search grounding is disabled by default.
- Use `gemini-3.1-flash-lite` for ordinary live generation with `gemini-2.5-flash-lite` configured as the temporary-overload and Search-safe fallback.
- Set `PROOFPILOT_API_CORS_ORIGINS` to an explicit comma-separated local frontend allowlist when using non-default ports; wildcard origins are rejected.
- Keep `PROOFPILOT_RATE_LIMITING_ENABLED=true` outside controlled local tests. Protected expensive routes fail closed when Redis is unavailable.
- API responses expose `X-Request-ID`; preserve this header through any future reverse proxy so local JSON request logs can be correlated with client-visible failures.
- Do not deploy with real credentials in frontend environment variables.
