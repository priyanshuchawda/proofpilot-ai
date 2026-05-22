# Deployment

The MVP is local-first. No paid hosted services are required.

## Local Services

```powershell
docker compose -f infra/docker-compose.yml up -d
```

PostgreSQL is available at `postgresql+asyncpg://proofpilot:proofpilot@127.0.0.1:55432/proofpilot`.

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

## Frontend

```powershell
pnpm --filter @proofpilot/web dev
```

Deployment to hosted platforms is deferred until the free-tier contract and secret-handling controls are complete.
