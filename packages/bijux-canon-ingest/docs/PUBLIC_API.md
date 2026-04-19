# Public API

## Supported entrypoints

- console script: `bijux-canon-ingest`
- Python package: `bijux_canon_ingest`
- package version: `bijux_canon_ingest.__version__`
- HTTP app factory: `bijux_canon_ingest.interfaces.http.app:create_app`
- schema contract: `apis/bijux-canon-ingest/v1/schema.yaml`

## Not automatically public

Modules under `application/`, `processing/`, `retrieval/`, and `infra/` are
implementation detail unless the package explicitly promotes them.
