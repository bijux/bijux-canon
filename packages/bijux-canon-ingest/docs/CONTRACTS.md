# CONTRACTS

Stable contracts in `bijux-canon-ingest` are:
- console entrypoint `bijux-canon-ingest`
- HTTP surface under `src/bijux_canon_ingest/interfaces/http/`
- API schema under `apis/bijux-canon-ingest/v1/schema.yaml`
- package-facing request, result, and configuration models

Package contracts should remain stable even if internals move between `application/`, `processing/`, `retrieval/`, and `infra/`.
