# Privacy And Security

## API Keys

- `GEMINI_API_KEY` is read only by backend services.
- Frontend code must never import Gemini SDKs or receive API keys.
- `.env`, `.env.local`, credentials, and generated secret files are ignored by Git.
- Local development reads `.env` from the repository root. Do not place keys in frontend files or `NEXT_PUBLIC_*` variables.

## Data Handling

- Gemini free-tier requests may be eligible for provider product improvement.
- The UI must warn users before upload to use public demo documents only.
- Server-side redaction must run before document chunks or prompts are sent to any model.
- Logs must include request metadata, not uploaded file content.

## Upload Safety

- Validate MIME type, extension, and size.
- Generate storage filenames server-side.
- Block path traversal.
- Preserve original filenames only as metadata after sanitization.

## Prompt Injection

Documents are untrusted evidence. The backend prompt contract must instruct models to ignore document text that attempts to override system or developer instructions.

## Local Infrastructure

The MVP uses local PostgreSQL, Redis, and Qdrant through Docker Compose. No paid hosted infrastructure is required.
