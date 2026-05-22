# ADR 0003: Free-Tier Gemini Routing

## Status

Accepted

## Context

The MVP must require only `GEMINI_API_KEY`, local Docker services, and free GitHub usage. Model availability and pricing can change.

## Decision

Treat model IDs and grounding availability as configuration. Default search grounding to disabled until the backend verifies the selected model is free-tier-safe. Never fall back to paid models automatically.

During MVP implementation and local live testing, use only `gemini-2.5-flash-lite` for generation routes. Revisit `gemini-3.5-flash` only during final production-readiness work.

## Consequences

- The app can degrade gracefully under quota or unavailable routes.
- Documentation must record verified pricing and capability decisions.
- Real Gemini smoke tests remain opt-in only.
