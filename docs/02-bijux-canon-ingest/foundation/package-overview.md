---
title: Package Overview
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Package Overview

`bijux-canon-ingest` turns source records into deterministic, retrieval-ready
material. It owns the point where inconsistent text, metadata, and file formats
become typed documents, stable chunks, embeddings, and local indexes.

The package is useful both as a small transformation library and as a complete
CSV-to-index command workflow.

## Processing Model

```mermaid
flowchart LR
    input["CSV rows or RawDoc values"]
    clean["normalize and validate"]
    chunk["split with stable offsets"]
    embed["attach deterministic or adapter embeddings"]
    index["build BM25 or NumPy cosine index"]
    query["retrieve or answer"]

    input --> clean --> chunk --> embed --> index --> query
```

Each stage keeps document identity attached to its output. Chunk offsets,
metadata, index fingerprints, and structured errors make it possible to trace a
retrieval candidate back to source preparation.

## Core Capabilities

| Capability | Public surface | Contract |
| --- | --- | --- |
| document modeling | `RawDoc`, `CleanDoc`, `Chunk` | immutable typed records with explicit identity |
| cleaning and chunking | `clean_doc`, `chunk_doc`, streaming variants | deterministic output for the same input and environment |
| result handling | `Result`, `Option`, validation collectors | failures remain values until a caller chooses a policy |
| embeddings | deterministic `hash16` and adapter boundaries | vector creation stays separate from document shaping |
| retrieval | BM25 and NumPy cosine indexes | serializable indexes with content/configuration fingerprints |
| interfaces | `bijux-canon-ingest` CLI and v1 HTTP API | command and schema boundaries over the same application services |

The package root exposes dependency-light primitives. Application orchestration
lives under `bijux_canon_ingest.application`; CLI and HTTP adapters live under
`bijux_canon_ingest.interfaces`.

## Minimal Library Use

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

assert chunks[0].doc_id == "policy-17"
assert chunks[0].text
```

Chunk configuration rejects non-positive sizes, negative overlap, and overlap
that is not smaller than the chunk size. Tail handling is explicit: callers can
emit a short final chunk, drop it, or pad it.

## Command Workflow

```bash
bijux-canon-ingest documents.csv --config pipeline.json --out chunks.jsonl

bijux-canon-ingest index build \
  --input documents.csv \
  --out artifacts/corpus.index \
  --backend bm25

bijux-canon-ingest retrieve \
  --index artifacts/corpus.index \
  --query "retention period" \
  --top-k 5
```

The preparation command writes JSON Lines atomically. Local retrieval indexes
use a versioned MessagePack representation and can be loaded by later command
invocations or through the application service.

## Ownership Boundary

Ingest owns transformations that happen before evidence is selected:

- parsing, normalization, validation, cleaning, and chunking;
- ingest-local embedding, deduplication, indexing, and retrieval assembly;
- serialization of prepared records and local retrieval indexes;
- structured ingest errors, retry safeguards, and processing diagnostics.

It does not own application-wide vector infrastructure, the meaning of a
reasoned claim, agent authority, or runtime acceptance and replay policy. Those
concerns belong to later packages even when they consume ingest artifacts.

## Compatibility

The `bijux-rag` distribution preserves the legacy `bijux_rag` import root and
`bijux-rag` command while delegating implementation to this package. New code
should use `bijux_canon_ingest` and `bijux-canon-ingest`. See
[compatibility commitments](../interfaces/compatibility-commitments.md) before
migrating an existing integration.

Continue with [installation and setup](../operations/installation-and-setup.md)
or the [entrypoint examples](../interfaces/entrypoints-and-examples.md).
