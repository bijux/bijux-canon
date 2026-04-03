# API v1 overview

The API is versioned and contract-driven. This page is descriptive; the canonical contract is `api/v1/schema.yaml`, and the generated JSON is `api/v1/openapi.v1.json` (derived; do not edit).

## Guarantees
- Versioned under `/api/v1`; breaking changes require a new version.
- Deterministic and non-deterministic executions are explicit; no implicit defaults.
- Error model is typed and mapped to HTTP status codes (see `api/errors.md`).

## Stability and versioning
- API schema is frozen via `schema.yaml`; drift is blocked by `make api-freeze`.
- Package versioning is tag-driven (hatch-vcs), and API stability is documented separately from package version.

## How to use
- Consult `api/v1/schema.yaml` to generate clients or validate requests/responses.
- CLI mirror: ingest → materialize → execute → explain → replay → compare.
- API endpoints: `/ingest` → `/artifact` → `/execute` → `/explain` → `/replay` (no `/compare` endpoint in v1).
- Optional routing fields: `vector_store`, `vector_store_uri` (ingest/execute/artifact) and `embed_model` (ingest).
- For non-deterministic executions, supply execution budgets and randomness profiles as required by the schema.

## References
- Canonical schema (YAML): `api/v1/schema.yaml`
- Generated JSON: `api/v1/openapi.v1.json`
- Errors: `api/errors.md`
