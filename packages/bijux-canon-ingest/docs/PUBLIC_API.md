# PUBLIC_API

Package-facing surfaces in `bijux-canon-ingest` are:
- console script: `bijux-canon-ingest`
- Python package: `bijux_canon_ingest`
- Python package version: `bijux_canon_ingest.__version__`
- HTTP app factory: `bijux_canon_ingest.interfaces.http.app:create_app`
- schema contract: `apis/bijux-canon-ingest/v1/schema.yaml`

Internal modules under `application/`, `processing/`, `retrieval/`, and `infra/` are implementation detail unless explicitly documented as public.
