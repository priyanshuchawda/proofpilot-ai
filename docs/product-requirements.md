# Product Requirements

## Mission

ProofPilot AI answers user questions from uploaded documents and free-tier-safe current web grounding with visible evidence, precise citations, retrieval traceability, and honest refusal when evidence is missing.

## Primary Users

- Hiring reviewers evaluating practical GenAI engineering quality.
- Developers and analysts testing document-grounded answer workflows.
- Hackathon judges looking for measurable differentiation beyond generic PDF chat.

## MVP Capabilities

- Create or select a workspace.
- Upload PDF, TXT, or Markdown documents.
- Track ingestion states from upload to ready.
- Ask document-grounded questions in Fast Mode or Verified Mode.
- Stream cited answers with evidence panels and trace details.
- Refuse unsupported answers.
- Run local evaluation datasets and view quality and latency metrics.

## Non-Goals For Initial MVP

- OCR for scanned PDFs.
- Paid hosted vector databases, search APIs, observability, or model routes.
- Autonomous agent loops for normal chat.
- Provider-managed File Search as the primary RAG system.

## Success Criteria

- Every important factual answer maps to real retrieved evidence.
- No frontend bundle or logs expose `GEMINI_API_KEY`.
- Local checks and CI pass without a real Gemini key.
- The demo shows retrieval, citation validation, no-evidence refusal, and privacy warnings.
