---
title: Data Contracts
audience: mixed
type: reference
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Data Contracts

Ingest has three distinct contract layers: source records, in-process chunk
values, and serialized boundary models. They are related, but they are not
interchangeable.

## Source Record

`RawDoc` represents one source row:

| Field | Type | Meaning |
| --- | --- | --- |
| `doc_id` | string | caller-supplied document identity |
| `title` | string | source title |
| `abstract` | string | text normalized and segmented by the pipeline |
| `categories` | string | source classification text |

`CleanDoc` carries the same fields after configured normalization. The pipeline
does not allocate a new document identity during cleaning.

## Retrieval Chunk

`ChunkWithoutEmbedding` is the segmentation contract. `Chunk` extends it with
an immutable embedding tuple.

| Field | Rule |
| --- | --- |
| `doc_id` | identifies the source record |
| `text` | contains the exact segmented text |
| `start`, `end` | integer source offsets; `start >= 0` and `end >= start` |
| `chunk_index` | non-negative ordinal within the source document |
| `title`, `category` | optional source context |
| `metadata` | read-only mapping for non-structural context |
| `embedding_spec` | optional dimensionality and model contract |
| `embedding` | final numeric vector, present on `Chunk` |
| `chunk_id` | SHA-256 identity derived from source ID, offsets, and text |

Metadata and the embedding specification do not participate in `chunk_id`.
Changing either may still change retrieval behavior, so an index fingerprint
must cover the full vector set and configuration rather than relying on chunk
IDs alone.

## Serialized Edge Model

The strict Pydantic `ChunkModel` is a versioned edge shape used by the
serialization adapters. Its contract is intentionally narrower:

```json
{
  "version": 1,
  "text": "a retrieval-ready passage",
  "metadata": {"source": "catalog.csv"},
  "embedding": [0.125, -0.25]
}
```

The model rejects unknown fields, coercion, empty text, non-finite vector
values, vectors longer than 8192 entries, and values outside the accepted
numeric range. `embedding` may be omitted; when present, it must be non-empty.
The computed text length is available in memory but excluded from canonical
serialization.

The core pipeline's retrieval `Chunk` and the edge `ChunkModel` serve different
purposes. The serialization adapters operate on the functional-programming
core chunk, not the retrieval chunk described above. `to_core_chunk()` retains
`text` and `metadata`; `from_core_chunk()` returns those same fields.
`embedding` is not transferred in either direction. Document identity, offsets,
ordinal, title, category, and embedding specification are outside this adapter.

## Identity and Projection Map

Every projection has a deliberate loss boundary:

| Transition | Preserved | Recomputed or changed | Not carried |
| --- | --- | --- | --- |
| `RawDoc` to `CleanDoc` | document ID, title, categories | normalized abstract | original abstract bytes |
| `CleanDoc` to retrieval chunk | document ID, selected text, source offsets | ordinal and `chunk_id` | unselected document text |
| unembedded to embedded chunk | all chunk fields | embedding tuple | nothing when the same chunk is enriched |
| `ChunkModel` to FP core chunk | text, metadata | core path becomes empty | embedding and retrieval identity |
| FP core chunk to `ChunkModel` | text, metadata | version defaults to `1` | path and embedding |

Only the first three transitions belong to the retrieval pipeline. The last two
are an edge-model interoperability path. Do not use that path to checkpoint a
retrieval chunk or to move vectors between systems.

## File Boundaries

The document CLI reads CSV records and writes one successful chunk per JSONL
line. Expected failures are returned or rendered separately; they are not
interleaved with successful rows in the output file. Treat the output as a
projection with an accompanying run context:

- write it to a new path or replace it atomically at the surrounding workflow;
- retain the input and effective configuration when reproducibility matters;
- validate every line and the expected row count before building an index; and
- do not infer an embedding model solely from vector length.

Expected boundary failures are represented with `Result` values. Unexpected
programming failures remain exceptions so corrupted or partial outputs are not
mistaken for successful domain results.

## Compatibility Rules

A change is compatibility-sensitive when it alters field meaning, stable ID
inputs, offset interpretation, serialization version, validation limits, or
the distinction between omitted and empty embeddings. Add a new version or an
explicit migration path for such changes; silently accepting both meanings
would make replay evidence ambiguous.

See [Execution Model](../architecture/execution-model.md) for how these values
move through the pipeline.
