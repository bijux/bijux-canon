---
title: Execution Model
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Execution Model

`bijux-canon-ingest` turns source records into deterministic, retrieval-ready
chunks. The main path is deliberately staged: each boundary has a named value,
and observation hooks cannot alter the result.

```mermaid
flowchart LR
    source["CSV or RawDoc stream"]
    keep["predicate filter"]
    clean["deterministic cleaning"]
    chunk["offset-aware chunking"]
    embed["embedding adapter"]
    dedup["structural deduplication"]
    result["chunks + observations"]

    source --> keep --> clean --> chunk --> embed --> dedup --> result
```

## Two Execution Shapes

The package exposes two complementary paths.

`iter_ingest_pipeline` and `iter_ingest_pipeline_core` preserve lazy iteration.
They are appropriate when callers need streaming composition and bounded
materialization. `run_ingest_pipeline_docs` materializes the input and stage
results so it can return deterministic counts, samples, warnings, and optional
tap observations.

Both paths preserve the same semantic order:

1. evaluate the document predicate;
2. normalize accepted documents;
3. split normalized text into chunks with source offsets;
4. embed each chunk through the supplied adapter;
5. remove structural duplicates; and
6. return chunks at the application boundary.

The path-based boundary, `run_ingest_pipeline_path`, adds source IO without
changing the core. Reader failures are returned as `Err`; successful reads enter
the same document pipeline and return `Ok((chunks, observations))`.

## Values at the Boundaries

The pipeline makes information loss explicit:

| Boundary | Value | Preserved identity |
| --- | --- | --- |
| source | `RawDoc` | document ID, title, abstract, categories |
| normalization | `CleanDoc` | source fields after deterministic text rules |
| segmentation | `ChunkWithoutEmbedding` | document ID, text, offsets, chunk index, metadata |
| retrieval handoff | `Chunk` | segmentation fields plus the embedding vector |
| run summary | `Observations` | document/chunk counts and bounded samples |

A chunk ID is derived from document ID, start offset, end offset, and text.
Reprocessing identical content with identical boundaries therefore produces the
same identity. Embedding dimensionality is checked where an `EmbeddingSpec` is
available rather than being hard-coded into the base chunk model.

## Configuration and Dependencies

`IngestConfig` owns data-affecting policy such as chunking and cleaning.
`IngestDeps` owns replaceable behavior such as cleaning, embedding, and taps.
This split lets tests and applications substitute infrastructure without
changing the pipeline's ordering rules.

Tap handlers receive immutable tuples of intermediate values. They are
observation-only: logging, metrics, and sampling are valid uses; mutating data
or steering execution is outside their contract.

## Determinism Boundary

Cleaning, chunk boundaries, stable IDs, deduplication, and observation sampling
are deterministic for the same inputs and configuration. An external embedder
may introduce its own model, version, or numerical variability. Callers that
require replay must pin those embedding inputs and retain the resulting
embedding specification with the index artifact.

## Implementation Map

- `application/pipeline.py` owns orchestration and materialized observations.
- `processing/chunking.py` and `processing/stages.py` own transformation stages.
- `core/types.py` owns the source, clean-document, and chunk value contracts.
- `interfaces/cli/` and `interfaces/http/` translate boundary requests.
- `safeguards/` contains reusable retry, breaker, cache, and resource policies;
  these policies are opt-in and do not silently wrap the core pipeline.

Continue with [Data Contracts](../interfaces/data-contracts.md) for serialized
shapes and [Failure Recovery](../operations/failure-recovery.md) for incident
handling.
