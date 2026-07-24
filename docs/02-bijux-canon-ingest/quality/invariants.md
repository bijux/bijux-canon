---
title: Invariants
audience: mixed
type: reference
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Invariants

`bijux-canon-ingest` turns source documents into immutable, addressable chunks.
Its guarantees concern transformation and provenance; they do not extend to the
semantic quality of a model supplied by a caller.

## Domain invariants

| Surface | Invariant | Failure behavior |
| --- | --- | --- |
| `RagEnv` | `chunk_size` and `sample_size` are positive integers | construction raises `ValueError` |
| `RagEnv` | `0 <= overlap < chunk_size` | construction raises `ValueError` |
| tail policy | value is `emit_short`, `drop`, or `pad` | construction raises `ValueError` |
| chunk span | offsets are integers, `start >= 0`, and `end >= start` | construction raises `ValueError` |
| chunk order | `chunk_index` is a non-negative integer | construction raises `ValueError` |
| metadata | input is a mapping and dictionary input is copied behind a read-only proxy | construction raises for a non-mapping |
| embedding specification | model is non-empty, dimension is positive, and metric is `cosine`, `dot`, or `l2` | construction raises `ValueError` |
| embedding boundary | a supplied vector has the dimension declared by its `EmbeddingSpec` | validated construction returns `Err` |

Core values are frozen dataclasses. A stage produces a new value rather than
mutating a document or chunk already observed by another stage.

## Identity and ordering

A chunk identifier is the SHA-256 digest of four values:

```text
document identifier : start offset : end offset : chunk text
```

The identifier is stable when all four inputs are stable. Titles, categories,
embeddings, and auxiliary metadata do not participate. Changing chunk size,
overlap, tail policy, text normalization, or document identity can therefore
change the identifier even if the source file name remains the same.

The document-oriented pipeline performs structural deduplication after
embedding. It orders chunks by document identifier and start offset, then keeps
the first occurrence of each structural key. This makes duplicate resolution
stable for the same inputs and configuration.

## Stage invariants

```mermaid
flowchart LR
    raw["RawDoc"] -->|predicate| kept["RawDoc"]
    kept -->|cleaner| clean["CleanDoc"]
    clean -->|chunker| span["ChunkWithoutEmbedding"]
    span -->|embedder| chunk["Chunk"]
    chunk -->|structural dedup| result["ordered chunks"]
```

- Filtering never changes a retained document.
- The standard cleaner deterministically trims, lowercases, and collapses
  whitespace in the abstract.
- Chunking advances by `chunk_size - overlap` and applies the selected tail
  policy consistently.
- Taps and probes observe stage values; they are not transformation stages.
- The path boundary returns `Result` for expected reader failures. Unexpected
  defects in supplied functions remain exceptions rather than being disguised
  as ordinary ingest outcomes.

## Determinism boundary

The standard hash embedder and lexical evaluation profile are deterministic.
An injected cleaner, reader, embedder, clock, storage adapter, or concurrent
effect becomes part of the caller's determinism boundary. Reproducibility
therefore requires recording the exact configuration and choosing adapters
whose behavior is stable for the intended environment.

## Executable evidence

The invariants are exercised by the domain, processing, result, streaming,
observability, and safeguard suites. The [test strategy](test-strategy.md)
maps each guarantee to the focused test families that defend it.
