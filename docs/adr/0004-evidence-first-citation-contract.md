# ADR 0004: Evidence-First Citation Contract

## Status

Accepted

## Context

The central product promise is grounded answers with precise citations and no invented evidence.

## Decision

Every answer must carry structured citation metadata. Important factual claims must map to retrieved chunk IDs or live grounding sources. Unsupported answers are downgraded or refused.

## Consequences

- Generation output requires schema validation.
- Citation IDs must be checked against actual retrieved evidence.
- The UI can show evidence trails and confidence labels honestly.
