# Privacy And Security

## API Keys

- `GEMINI_API_KEY` is read only by backend services.
- Browser access uses a validated `PROOFPILOT_API_CORS_ORIGINS` allowlist; wildcard origins and URL-like values containing paths, credentials, query strings, or fragments are rejected.
- Frontend code must never import Gemini SDKs or receive API keys.
- `.env`, `.env.local`, credentials, and generated secret files are ignored by Git.
- Local development reads `.env` from the repository root. Do not place keys in frontend files or `NEXT_PUBLIC_*` variables.
- Uploads, model-backed queries, streamed queries, and evaluation runs are protected by Redis-backed rate limits. Redis keys store a hash of the backend-observed caller identifier rather than raw IP addresses or tokens.

## Data Handling

- Gemini free-tier requests may be eligible for provider product improvement.
- The UI must warn users before upload to use public demo documents only.
- Server-side redaction must run before document chunks or prompts are sent to any model.
- Request logs include only trace-safe metadata: request ID, method, route path without query string, status code, duration, rate-limit outcome, and safe query-run correlation fields when available. They must not include uploaded file content, prompt text, authorization headers, query strings, or API keys.
- Local session ownership uses `X-ProofPilot-Session` as a development-only identity boundary. When `PROOFPILOT_WORKSPACE_OWNERSHIP_ENABLED=true`, foreign workspace, document, query, and query-run trace access returns `404` to avoid confirming resource existence.

## Upload Safety

- Validate MIME type, extension, and size.
- Generate storage filenames server-side.
- Block path traversal.
- Preserve original filenames only as metadata after sanitization.
- Redact common secret formats before chunk text is persisted for downstream model-bound use.
- Supported MVP uploads are PDF, TXT, Markdown, and no OCR is performed.

## Prompt Injection

Documents are untrusted evidence. The backend prompt contract must instruct models to ignore document text that attempts to override system or developer instructions.

## Local Infrastructure

The MVP uses local PostgreSQL, Redis, and Qdrant through Docker Compose. No paid hosted infrastructure is required.
