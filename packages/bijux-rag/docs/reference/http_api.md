# HTTP API (FastAPI)

FastAPI app lives in `bijux_rag.boundaries.web.fastapi_app`. The published OpenAPI schema is versioned at `api/v1/schema.yaml`.

- `POST /v1/index/build` — build an index from documents (bm25 or numpy-cosine).
- `POST /v1/retrieve` — retrieve top-k candidates from a saved index.
- `POST /v1/ask` — generate an answer with citations grounded in retrieved chunks.
- `POST /v1/chunks` — legacy chunk/embed endpoint.
- `GET /v1/healthz` — health check.

To view the full OpenAPI spec in docs, mkdocs renders `api/v1/schema.yaml`. Clients can be generated directly from that file.
