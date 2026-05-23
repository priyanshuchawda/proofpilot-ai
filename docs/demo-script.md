# Demo Script

1. Start Docker services, FastAPI, and Next.js locally.
2. Show the privacy warning, free-tier mode, and disabled Search grounding status.
3. Create a workspace and upload only public demo documents.
4. Confirm ingestion status reaches `ready`.
5. Ask an answerable question in Fast Mode.
6. Switch to Verified Mode and show route, freshness label, citations, and evidence.
7. Ask a no-evidence or freshness-required question and show safe refusal.
8. Ask a conflicting-source question and show contradiction metadata when available.
9. Run the evaluation dashboard and identify deterministic metrics.
10. Show docs and local quality-gate results. GitHub Actions are deferred until final hardening.

Do not show `.env`, API keys, raw secrets, private documents, or screenshots containing credentials.
