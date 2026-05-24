# ADR 0003: Free-Tier Gemini Routing

## Status

Accepted

## Context

The MVP must require only `GEMINI_API_KEY`, local Docker services, and free GitHub usage. Model availability and pricing can change.

## Decision

Treat model IDs and grounding availability as configuration. Default search grounding to disabled until the backend verifies the selected model is free-tier-safe. Never fall back to paid models automatically.

Use `gemini-3.1-flash-lite` for ordinary non-search generation when configured. Use `gemini-2.5-flash-lite` as the Search-grounding fallback because the 2026-05-24 official pricing review marks Gemini 3.1 Flash-Lite free-tier Search grounding as unavailable while Gemini 2.5 Flash-Lite remains free-tier-safe up to documented quota.

## Consequences

- The app can degrade gracefully under quota or unavailable routes.
- Documentation must record verified pricing and capability decisions.
- Real Gemini smoke tests remain opt-in only.
- Search grounding remains disabled by default. If it is enabled and the freshness model is not free-tier-safe for Search, the backend chooses `GEMINI_SEARCH_GROUNDING_FALLBACK_MODEL`.
- Successful Search-grounded responses require web-source grounding metadata, inline support mappings, and Google's Search Suggestions content; otherwise the application refuses instead of presenting an un-attributed current answer.
- Retryable quota and overload failures are surfaced to users without selecting a paid model.
