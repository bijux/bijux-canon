---
title: Entrypoints and Examples
audience: mixed
type: how-to
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Entrypoints and Examples

Choose an entrypoint by boundary: use the package root for in-process
transformations, the console command for files and local indexes, and the v1
HTTP adapter for a service boundary. All three routes preserve document
identity and make validation failures explicit.

## Python: clean and chunk one document

The package root is dependency-light and is the preferred import surface for
stable ingest primitives.

```python
from bijux_canon_ingest import RagEnv, RawDoc, chunk_doc, clean_doc

source = RawDoc(
    doc_id="policy-17",
    title="Retention policy",
    abstract="  Keep signed run records for seven years.  ",
    categories="governance",
)

clean = clean_doc(source)
chunks = chunk_doc(clean, RagEnv(chunk_size=48, overlap=8))

for chunk in chunks:
    print(chunk.doc_id, chunk.start, chunk.end, chunk.text)
```

`RagEnv` rejects a non-positive chunk size and an overlap that is negative or
not smaller than the chunk size. The default tail policy emits a final short
chunk; callers can choose `drop` or `pad` explicitly when that is the intended
corpus contract.

## CLI: prepare a configured corpus

The pipeline form reads source rows from CSV, applies the steps declared in a
JSON configuration, and optionally writes chunk records as JSON Lines.

```bash
bijux-canon-ingest documents.csv \
  --config pipeline.json \
  --out artifacts/ingest/chunks.jsonl
```

Configuration values can be overridden without editing the file:

```bash
bijux-canon-ingest documents.csv \
  --config pipeline.json \
  --set chunk.params.chunk_size=384 \
  --out artifacts/ingest/chunks.jsonl
```

Pipeline configuration or argument errors exit with status `2`. Processing and
adapter failures exit with status `1`; successful completion exits with status
`0`.

## CLI: build and query a local index

Use the retrieval subcommands when the ingest package should own the entire
local preparation-and-query loop.

```bash
bijux-canon-ingest index build \
  --input documents.csv \
  --out artifacts/ingest/corpus.index \
  --backend bm25 \
  --chunk-size 384 \
  --overlap 48

bijux-canon-ingest retrieve \
  --index artifacts/ingest/corpus.index \
  --query "retention period" \
  --top-k 5 \
  --out artifacts/ingest/candidates.json

bijux-canon-ingest ask \
  --index artifacts/ingest/corpus.index \
  --query "How long are signed records retained?" \
  --format json \
  --out artifacts/ingest/answer.json
```

`bm25` is the deterministic lexical backend. `numpy-cosine` supports the
deterministic `hash16` embedder or the optional `sbert` adapter. Treat model
choice and model version as part of an index's reproducibility boundary.

## HTTP: create chunks

Run the packaged ASGI application with an ASGI server:

```bash
uvicorn bijux_canon_ingest.interfaces.http.app:app --host 127.0.0.1 --port 8000
```

Then submit one or more documents:

```bash
curl --fail-with-body http://127.0.0.1:8000/v1/chunks \
  --header 'content-type: application/json' \
  --data '{
    "chunk_size": 128,
    "overlap": 16,
    "include_embeddings": false,
    "docs": [
      {
        "doc_id": "policy-17",
        "title": "Retention policy",
        "category": "governance",
        "text": "Keep signed run records for seven years."
      }
    ]
  }'
```

The service also exposes `POST /v1/index/build`, `POST /v1/retrieve`, and
`POST /v1/ask`. Index identifiers live in the process-local index store, so
they do not survive an application restart. Use a durable application-owned
adapter when index persistence is a requirement.

The authoritative request and response contract is the checked-in
[`v1 schema`](https://github.com/bijux/bijux-canon/blob/main/apis/bijux-canon-ingest/v1/schema.yaml).
