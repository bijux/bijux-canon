# Usage

## CLI
Process documents, build indexes, retrieve, and ask via the CLI:

```bash
# Build an index directly from a CSV corpus
bijux-canon-ingest index build --input data/arxiv_cs_abstracts_10k.csv --out artifacts/bijux-canon-ingest/index.msgpack --backend bm25

# Retrieve top-k matches
bijux-canon-ingest retrieve --index artifacts/bijux-canon-ingest/index.msgpack --query "functional programming in RAG" --top-k 10

# Ask with grounded response (citations from retrieved)
bijux-canon-ingest ask --index artifacts/bijux-canon-ingest/index.msgpack --query "explain ingest effects" --top-k 5 --format json

# Run eval suite (pinned corpus/queries)
bijux-canon-ingest eval --suite tests/eval --index artifacts/bijux-canon-ingest/index.msgpack
```

- `--backend bm25|numpy-cosine` (deterministic profiles).
- `--embedder hash16|sbert` for vector indexes.
- `--filter key=value` for metadata filtering (AND).
- See `bijux-canon-ingest --help` for full options.

## Library
Build composable ingest and retrieval flows programmatically:

```python
from bijux_canon_ingest.core.types import RawDoc
from bijux_canon_ingest.application.indexing import ingest_docs_to_chunks
from bijux_canon_ingest.application.service import IngestService
from bijux_canon_ingest.result import is_ok

docs = [
    RawDoc(
        doc_id="1",
        title="Ingest Intro",
        abstract="Composable pipelines turn documents into searchable chunks.",
        categories="docs",
    )
]
chunks = ingest_docs_to_chunks(docs=docs, env=RagEnv(chunk_size=256))

service = IngestService()
index_result = service.build_index(docs, backend="bm25")
if is_ok(index_result):
    answer_result = service.ask(index_result.value, query="what is ingestion?", top_k=5)
    print(chunks[0].text, answer_result)
```

Leverage effects for resilience with `retry_idempotent`, `async_gen_map`, and `resilient_mapper`.

## API (FastAPI)
Launch the HTTP server:

```bash
uvicorn bijux_canon_ingest.interfaces.http.app:app --host 0.0.0.0 --port 8000 --reload
```

Endpoints (v1 prefix):
- `GET /healthz`
- `POST /index/build`
- `POST /retrieve`
- `POST /ask`
- `POST /chunks`

Full schema in docs/reference/http_api.md (OpenAPI compliant).
