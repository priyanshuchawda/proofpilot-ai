# Deployment

The MVP is local-first. No paid hosted services are required.

## Local Services

```powershell
docker compose -f infra/docker-compose.yml up -d
```

## Backend

```powershell
cd services/api
uv run uvicorn app.main:app --reload
```

## Frontend

```powershell
pnpm --filter @proofpilot/web dev
```

Deployment to hosted platforms is deferred until the free-tier contract and secret-handling controls are complete.
