# ADR 0006: Validated Final SSE Before Provider-Native Streaming

Date: 2026-05-25

## Status

Accepted

## Context

The Gemini API supports streaming text generation with `generate_content_stream` in the official Python SDK. However, ProofPilot's evidence-first contract requires citation ID validation and paragraph-level citation coverage before factual answer text is treated as reliable.

## Decision

Keep the MVP query stream as backend SSE over a finalized structured answer. The backend may stream deltas to the browser only after retrieval, answer generation, citation ID validation, and paragraph-level citation validation have completed. Provider-native Gemini streaming remains disabled until a future adapter can buffer, validate, and only then release supported text without exposing unsupported partial claims.

## Consequences

- Users still receive an SSE transport and progressive UI rendering.
- Unsupported factual paragraphs are refused before any final answer is shown.
- Time-to-first-token is not provider-native yet.
- The design preserves no-chain-of-thought behavior and evidence-first semantics.
