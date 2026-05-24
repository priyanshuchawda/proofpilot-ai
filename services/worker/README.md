# ProofPilot Worker

The local MVP ingestion worker shares the typed backend package and processes documents queued by the API in Redis.

Run one worker in a separate PowerShell terminal:

```powershell
cd services/api
uv run python -m app.ingestion.worker
```

The worker reserves uploaded documents into an in-flight Redis list, advances persisted document status through parsing, chunking, indexing, and readiness, and acknowledges terminal processing. When restarted, it requeues unacknowledged in-flight work and resumes committed processing stages without recreating chunks. This recovery contract supports one active local worker process.
