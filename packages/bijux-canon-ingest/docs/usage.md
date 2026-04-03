# Usage

## CLI
Process documents, build indexes, retrieve, and ask via the CLI:

```bash
# Ingest and chunk CSV docs (outputs msgpack chunks)
bijux-canon-ingest process --input data/arxiv_cs_abstracts_10k.csv --output artifacts/bijux-canon-ingest/chunks.msgpack --chunk-size 512

# Build index from chunks (BM25 or vector)
bijux-canon-ingest index-build --input artifacts/bijux-canon-ingest/chunks.msgpack --output artifacts/bijux-canon-ingest/index.msgpack --backend bm25

# Retrieve top-k matches
bijux-canon-ingest retrieve --index artifacts/bijux-canon-ingest/index.msgpack --query "functional programming in RAG" --top-k 10

# Ask with grounded response (citations from retrieved)
bijux-canon-ingest ask --index artifacts/bijux-canon-ingest/index.msgpack --query "explain RAG effects" --top-k 5 --format json

# Run eval suite (pinned corpus/queries)
bijux-canon-ingest eval --suite tests/eval --index artifacts/bijux-canon-ingest/index.msgpack
```

- `--backend bm25|numpy-cosine` (deterministic profiles).
- `--embedder default|custom` for vector indexes.
- `--filter key=value` for metadata filtering (AND).
- See `bijux-canon-ingest --help` for full options.

## Library
Build composable RAG pipelines programmatically:

```python
from bijux_rag.core.types import RawDoc
from bijux_rag.application.pipelines.configured import (
    PipelineConfig,
    StepConfig,
    build_rag_pipeline,
)
from bijux_rag.application.service import IngestService

docs = [RawDoc(doc_id="1", title="RAG Intro", abstract="Retrieval-Augmented Generation combines search and LLMs.")]
pipeline = build_rag_pipeline(
    PipelineConfig(
        steps=(
            StepConfig("clean"),
            StepConfig("chunk", {"chunk_size": 256}),
            StepConfig("embed"),
        )
    )
)
embedded = [result.value for result in pipeline(iter(docs))]

app = IngestService()  # Configurable app
index = app.build_index(embedded, backend="bm25").unwrap()
retrieved = app.retrieve(index, query="what is RAG?", top_k=5).unwrap()
answer = app.ask(index, query="explain RAG", top_k=5, rerank=True).unwrap()["answer"]
print(answer)
```

Leverage effects for resilience: wrap in `retry_idempotent` or `async_with_resilience`.

## API (FastAPI)
Launch the HTTP server:

```bash
uvicorn bijux_rag.interfaces.http.app:app --host 0.0.0.0 --port 8000 --reload
```

Endpoints (v1 prefix):
- `GET /health` → `{"status": "ok"}`
- `POST /index/build` (JSON docs array, backend, chunk params) → index ID.
- `POST /retrieve` (index_id, query, filters?, top_k) → ranked results.
- `POST /ask` (index_id, query, top_k, rerank?) → grounded answer with citations.
- `POST /chunks` (docs, chunk_size, overlap) → chunked output.

Full schema in docs/reference/http_api.md (OpenAPI compliant).
