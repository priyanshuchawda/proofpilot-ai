# Demo Script

1. Start Docker services, FastAPI, the ingestion worker, and Next.js locally.
2. Confirm the dashboard shows `API healthy`, then show the privacy warning, free-tier mode, and disabled Search grounding status.
3. Create or select a workspace in the dashboard and upload only public demo documents.
4. Confirm ingestion moves from `uploaded` to `ready`; a processing failure presents only safe retry guidance.
5. Ask an answerable question in Fast Mode.
6. Switch to Verified Mode and show route, freshness label, citations, evidence, retrieved candidates, latency, and retrieval trace.
7. Ask a no-evidence or freshness-required question and show safe refusal.
8. Ask a conflicting-source question and show contradiction metadata when available.
9. Run the evaluation dashboard and identify deterministic metrics.
10. Show docs and local quality-gate results. GitHub Actions are deferred until final hardening.

Do not show `.env`, API keys, raw secrets, private documents, or screenshots containing credentials.

If another local project owns backend port `8000`, run the backend on a free port and start the frontend with `NEXT_PUBLIC_API_BASE_URL` pointing to that local backend. If the frontend also uses a non-default port, configure its exact origin in `PROOFPILOT_API_CORS_ORIGINS`.
