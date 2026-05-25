# ADR 0005: Local Session Ownership Boundary

Date: 2026-05-25

## Status

Accepted

## Context

ProofPilot is local-first today, but open workspace IDs are not a safe foundation for a future multi-user deployment. The project also cannot depend on paid auth services for the MVP.

## Decision

Add a local identity boundary based on `X-ProofPilot-Session` with a stable `local-anonymous` fallback for single-user local demos. Workspaces store `owner_session_id`. When `PROOFPILOT_WORKSPACE_OWNERSHIP_ENABLED=true`, workspace listing, document status, document listing/upload, query execution, and query-run trace access are scoped to the current local session and return `404` for foreign resources.

This is not a production authentication scheme. It is an ownership boundary and integration point for a later first-party session cookie or external auth provider.

## Consequences

- Existing local demos continue to work with ownership enforcement disabled by default.
- New workspaces still receive an owner session ID, so the migration path is explicit.
- Cross-session access can be tested locally without paid infrastructure.
- Rate-limit and cache-key design can later replace IP/session labels with authenticated principal IDs without changing workspace ownership semantics.
