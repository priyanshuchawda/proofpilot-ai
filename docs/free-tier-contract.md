# Gemini Free-Tier Contract

Date verified: 2026-05-24

Grounding re-check: 2026-05-24

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

The 2026-05-24 re-check was verified directly against official `ai.google.dev` pages:

- https://ai.google.dev/gemini-api/docs/google-search
- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/models/gemini
- https://ai.google.dev/gemini-api/docs/rate-limits

## Selected Configuration Defaults

- Development generation model: `gemini-2.5-flash-lite`
- Development lightweight model: `gemini-2.5-flash-lite`
- Development freshness model: `gemini-2.5-flash-lite`
- Search-grounding fallback model: `gemini-2.5-flash-lite`
- Embedding model: `gemini-embedding-2`, disabled by default behind `GEMINI_EMBEDDINGS_ENABLED=false`
- SDK: official Python `google-genai`

All model IDs are configuration values, not hard-coded architecture assumptions. Current local development intentionally uses `gemini-2.5-flash-lite` for ordinary generation, lightweight fallback, freshness detection, and Search fallback. Later production hardening may review higher-quality configured models, but Search grounding must still use a model whose official pricing table marks free-tier grounding as available; if the freshness model is not free-tier-safe for Search, the backend selects `GEMINI_SEARCH_GROUNDING_FALLBACK_MODEL`.

## Free-Tier-Safe Capabilities

- Server-side API key calls from the Python backend.
- Text generation with selected free-tier-capable Flash models, subject to rate limits.
- Structured JSON outputs for answer contracts and routing outputs.
- Streaming generation for interactive responses.
- Google Search grounding only when feature-flagged and only on models whose pricing table marks free-tier grounding as available.
- As of the 2026-05-24 re-check, official pricing lists Gemini 2.5 Flash-Lite Search grounding as free tier up to 500 RPD shared with Flash RPD, while Gemini 3.1 Flash-Lite free-tier Search grounding is marked unavailable. ProofPilot therefore falls back to `gemini-2.5-flash-lite` for Search.
- Gemini embeddings with `gemini-embedding-2` are free-tier available subject to rate limits and are opt-in through `GEMINI_EMBEDDINGS_ENABLED=true`.

## Disabled Or Deferred

- Provider-managed File Search is disabled for MVP. The official docs describe File Search as a managed RAG tool with pricing interactions around embedding and model tokens; ProofPilot uses custom local RAG to demonstrate retrieval architecture and avoid unclear cost paths.
- Context caching is not used in the MVP. Some pricing rows mark it unavailable on free tier for selected models.
- Google Maps grounding, computer use, custom tools endpoints, Vertex AI, and paid tiers are disabled.
- Real Gemini smoke tests are manual only and guarded by `RUN_GEMINI_SMOKE=1`.
- Real cited-answer generation smoke tests are manual only and guarded by `RUN_GEMINI_ANSWER_SMOKE=1`.
- Real Gemini embedding calls are disabled by default for deterministic local testing. When `GEMINI_EMBEDDINGS_ENABLED=true` and `GEMINI_API_KEY` is present, the backend uses the official `google-genai` SDK with `gemini-embedding-2`; otherwise it falls back to deterministic local embeddings without exposing secrets.
- Google Search grounding remains disabled by default even though Gemini 2.5 Flash-Lite is documented as free-tier-safe up to quota. Freshness-required questions refuse clearly unless `GEMINI_SEARCH_GROUNDING_ENABLED=true` is deliberately set.
- When Search grounding is deliberately enabled, accepted responses must carry `groundingChunks`, `groundingSupports`, and `searchEntryPoint.renderedContent`. ProofPilot maps these to inline `[web-n]` labels, distinct live-web sources, and an isolated Search Suggestions display; missing required metadata results in refusal.
- Provider-managed File Search remains disabled. It can be investigated later behind a disabled-by-default adapter after another pricing and privacy review.

## Known Quotas And Degradation

- Free-tier limits vary by selected model and tool. The app must surface quota errors without switching to paid routes.
- Search grounding for Gemini 2.5 Flash and Flash-Lite is documented as free up to 500 requests per day shared across the Flash and Flash-Lite RPD. Paid tiers have higher free shared limits and then bill per grounded prompt.
- Gemini 3 Search grounding has separate free prompt language for supported models, but the Gemini 3.1 Flash-Lite pricing row marks free-tier Search grounding as unavailable. The app must not use Gemini 3.1 Flash-Lite for Search unless official pricing changes and this document is updated.
- If quota is exhausted, the backend returns `route_quota_exhausted`, preserves retrieval evidence, and allows retry later.
- If ordinary document generation receives HTTP `503` from its configured primary model, the backend may retry once using the configured free-tier lightweight model and reports which model succeeded. A failed fallback or a Search-path overload returns `route_provider_unavailable`. HTTP `429` returns `route_quota_exhausted` without another model call.

## Live Smoke Result

- 2026-05-23: Manual opt-in smoke test passed with `RUN_GEMINI_SMOKE=1` using `gemini-2.5-flash-lite`.
- 2026-05-24: Provider fallback tests verify that `gemini-3.1-flash-lite` is not treated as free-tier-safe for Search and falls back to `gemini-2.5-flash-lite`.
- 2026-05-24: Manual opt-in embedding smoke passed with `RUN_GEMINI_EMBEDDING_SMOKE=1` using `gemini-embedding-2`.
- 2026-05-24: Manual opt-in Search grounding smoke passed with `RUN_GEMINI_SEARCH_SMOKE=1` using the configured free-tier-safe fallback model.
- 2026-05-24: A later opt-in Search retry returned HTTP `503 UNAVAILABLE` due to temporary model demand; this is a provider-availability condition rather than an API-key authentication failure and is covered by the graceful-degradation path.
- 2026-05-24: Issue #41 live endpoint smoke with `gemini-3.1-flash-lite` configured for ordinary generation and `gemini-2.5-flash-lite` selected for Search returned a grounded, web-only freshness answer with 7 live sources, inline source labels, and required Search Suggestions metadata.
- 2026-05-25: Manual opt-in cited-answer smoke passed with `RUN_GEMINI_ANSWER_SMOKE=1` using `gemini-2.5-flash-lite` against public synthetic evidence.
- Standard tests remain mocked or skipped and do not require `GEMINI_API_KEY`.

## Privacy Contract

Official API-key guidance says server-side calls are the most secure way to keep API keys confidential. ProofPilot follows that by keeping Gemini calls in `services/api` and later `services/worker`.

Gemini free-tier usage may be used to improve provider products. ProofPilot must show a privacy warning before uploads and must redact common secrets before sending chunks or prompts to Gemini.
