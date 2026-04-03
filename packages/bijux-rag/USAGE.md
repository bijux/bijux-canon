# Usage

## CLI
Process documents, build indexes, retrieve, and ask via the CLI:

```bash
# Ingest and chunk CSV docs (outputs msgpack chunks)
bijux-rag process --input data/arxiv_cs_abstracts_10k.csv --output artifacts/chunks.msgpack --chunk-size 512

# Build index from chunks (BM25 or vector)
bijux-rag index-build --input artifacts/chunks.msgpack --output artifacts/index.msgpack --backend bm25

# Retrieve top-k matches
bijux-rag retrieve --index artifacts/index.msgpack --query "functional programming in RAG" --top-k 10

# Ask with grounded response (citations from retrieved)
bijux-rag ask --index artifacts/index.msgpack --query "explain RAG effects" --top-k 5 --format json

# Run eval suite (pinned corpus/queries)
bijux-rag eval --suite tests/eval --index artifacts/index.msgpack
```

- `--backend bm25|numpy-cosine` (deterministic profiles).
- `--embedder default|custom` for vector indexes.
- `--filter key=value` for metadata filtering (AND).
- See `bijux-rag --help` for full options.

## Library
Build composable RAG pipelines programmatically:

```python
from bijux_rag.core.rag_types import RawDoc
from bijux_rag.domain.effects.async_ import async_gen_from_list, async_gen_map
from bijux_rag.policies.chunking import fixed_size_chunk
from bijux_rag.pipelines.embedding import embed_docs
from bijux_rag.rag.app import RagApp
from bijux_rag.result.types import unwrap

docs = [RawDoc(doc_id="1", title="RAG Intro", abstract="Retrieval-Augmented Generation combines search and LLMs.")]
chunks = list(async_gen_map(async_gen_from_list(docs), fixed_size_chunk))  # Streaming chunking
embedded = list(embed_docs(chunks))  # Embed pipeline

app = RagApp()  # Configurable app
index = app.build_index(embedded, backend="bm25").unwrap()
retrieved = app.retrieve(index, query="what is RAG?", top_k=5).unwrap()
answer = app.ask(index, query="explain RAG", top_k=5, rerank=True).unwrap()["answer"]
print(answer)
```

Leverage effects for resilience: wrap in `retry_idempotent` or `async_with_resilience`.

## API (FastAPI)
Launch the HTTP server:

```bash
uvicorn bijux_rag.boundaries.web.fastapi_app:app --host 0.0.0.0 --port 8000 --reload
```

Endpoints (v1 prefix):
- `GET /health` → `{"status": "ok"}`
- `POST /index/build` (JSON docs array, backend, chunk params) → index ID.
- `POST /retrieve` (index_id, query, filters?, top_k) → ranked results.
- `POST /ask` (index_id, query, top_k, rerank?) → grounded answer with citations.
- `POST /chunks` (docs, chunk_size, overlap) → chunked output.

Full schema in docs/reference/http_api.md (OpenAPI compliant).
