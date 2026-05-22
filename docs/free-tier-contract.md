# Gemini Free-Tier Contract

Date verified: 2026-05-23

Grounding re-check: 2026-05-23

Sources checked through the official Gemini API documentation MCP:

- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/billing
- https://ai.google.dev/gemini-api/docs/embeddings
- https://ai.google.dev/gemini-api/docs/google-search
- https://ai.google.dev/gemini-api/docs/file-search
- https://ai.google.dev/gemini-api/docs/structured-output
- https://ai.google.dev/gemini-api/docs/quickstart
- https://ai.google.dev/gemini-api/docs/api-key
- https://ai.google.dev/gemini-api/docs/libraries

The Gemini documentation MCP was rate-limited during the 2026-05-23 grounding re-check, so the current grounding decision was verified directly against official `ai.google.dev` pages:

- https://ai.google.dev/gemini-api/docs/google-search
- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/models/gemini

## Selected Configuration Defaults

- Development generation model: `gemini-2.5-flash-lite`
- Development lightweight model: `gemini-2.5-flash-lite`
- Development freshness model: `gemini-2.5-flash-lite` with Search grounding disabled by default
- Later production review candidate: `gemini-3.5-flash`
- Embedding candidate: `gemini-embedding-2`
- SDK: official Python `google-genai`

All model IDs are configuration values, not hard-coded architecture assumptions. During MVP implementation and local live testing, only `gemini-2.5-flash-lite` is enabled for generation routes. Gemini 3.5 models are deferred until final production-readiness review.

## Free-Tier-Safe Capabilities

- Server-side API key calls from the Python backend.
- Text generation with selected free-tier-capable Flash models, subject to rate limits.
- Structured JSON outputs for answer contracts and routing outputs.
- Streaming generation for interactive responses.
- Google Search grounding only when feature-flagged and only on models whose pricing table marks free-tier grounding as available.
- As of the 2026-05-23 re-check, official pricing lists Gemini 2.5 Flash-Lite Search grounding as free tier up to 500 RPD shared with Flash RPD, and the Google Search docs list Gemini 2.5 Flash-Lite as supported.

## Disabled Or Deferred

- Provider-managed File Search is disabled for MVP. The official docs describe File Search as a managed RAG tool with pricing interactions around embedding and model tokens; ProofPilot uses custom local RAG to demonstrate retrieval architecture and avoid unclear cost paths.
- Context caching is not used in the MVP. Some pricing rows mark it unavailable on free tier for selected models.
- Google Maps grounding, computer use, custom tools endpoints, Vertex AI, and paid tiers are disabled.
- Real Gemini smoke tests are manual only and guarded by `RUN_GEMINI_SMOKE=1`.
- Real Gemini embedding calls are deferred during current development because live testing is limited to `gemini-2.5-flash-lite` generation only. The code uses a deterministic local embedding provider for tests and vector plumbing until the embedding model is explicitly re-enabled.
- Google Search grounding remains disabled by default even though Gemini 2.5 Flash-Lite is documented as free-tier-safe up to quota. Freshness-required questions refuse clearly unless `GEMINI_SEARCH_GROUNDING_ENABLED=true` is deliberately set.

## Known Quotas And Degradation

- Free-tier limits vary by selected model and tool. The app must surface quota errors without switching to paid routes.
- Search grounding for Gemini 2.5 Flash and Flash-Lite is documented as free up to 500 requests per day shared across the Flash and Flash-Lite RPD. Paid tiers have higher free shared limits and then bill per grounded prompt.
- Gemini 3 search grounding has separate monthly free prompt limits on supported models, but several Gemini 3 pricing rows mark free tier as not available. The app must require explicit model and feature-flag confirmation before enabling Gemini 3 search.
- If quota is exhausted, the backend returns `route_quota_exhausted`, preserves retrieval evidence, and allows retry later.

## Live Smoke Result

- 2026-05-23: Manual opt-in smoke test passed with `RUN_GEMINI_SMOKE=1` using `gemini-2.5-flash-lite`.
- Standard tests remain mocked or skipped and do not require `GEMINI_API_KEY`.

## Privacy Contract

Official API-key guidance says server-side calls are the most secure way to keep API keys confidential. ProofPilot follows that by keeping Gemini calls in `services/api` and later `services/worker`.

Gemini free-tier usage may be used to improve provider products. ProofPilot must show a privacy warning before uploads and must redact common secrets before sending chunks or prompts to Gemini.
