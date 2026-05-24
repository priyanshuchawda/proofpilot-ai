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
- Live web citations must be mapped from Gemini grounding support metadata and shown with distinct `web-n` labels.
- Search-grounded responses are accepted only when required Search Suggestions display metadata is present.
- The UI can show evidence trails and confidence labels honestly.
