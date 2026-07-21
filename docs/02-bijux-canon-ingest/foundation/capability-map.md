---
title: Capability Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Capability Map

`bijux-canon-ingest` combines deterministic document preparation with a compact
local retrieval path and reusable execution safeguards. The capabilities share
typed records, explicit results, and configuration, but they retain distinct
ownership and evidence.

```mermaid
flowchart LR
    source["source rows and text"]
    prepare["filter, clean, chunk"]
    enrich["embed, observe, deduplicate"]
    persist["CSV / JSONL / local index"]
    retrieve["rank, answer, evaluate"]
    evidence["IDs, offsets, citations, diagnostics"]

    source --> prepare --> enrich --> persist --> retrieve --> evidence
```

## Preparation capabilities

| Capability | Primary implementation | Produced evidence | Boundary |
| --- | --- | --- | --- |
| Typed source admission | `core/types.py`, readers, strict interface models | `RawDoc` or explicit read failure | does not establish source accuracy or licensing |
| Deterministic cleaning | `processing/`, configured cleaners and rules | immutable `CleanDoc` and observations | offsets after cleaning address normalized text |
| Policy-driven filtering | predicates and safe rule evaluation | retained/rejected records and reports | caller policy, not source governance |
| Overlapping chunking | chunkers, tail policies, span validation | stable chunk index, offsets, text, and SHA-256 identity | identity changes when source, span, or text changes |
| Embedding | hash baseline and optional sentence-transformers adapter | vector plus optional `EmbeddingSpec` | hash vectors are not semantic evidence |
| Structural deduplication | document pipeline dedup stage | deterministic first occurrence by structural key | does not detect paraphrases or semantic duplicates |
| Streaming composition | `streaming/`, `fp/`, and result folds | ordered lazy values or typed errors | observations that need the full corpus materialize it |

## Retrieval and execution capabilities

| Capability | Primary implementation | Produced evidence | Boundary |
| --- | --- | --- | --- |
| Local lexical index | `retrieval/` BM25 implementation | persisted index identity, ordered scores and chunks | package-local reference path |
| Local dense index | NumPy cosine implementation | index metadata, embedding identity, ranked chunks | scores are specific to metric and model |
| Extractive answering | retrieval answer workflow | answer text and resolvable chunk citations | does not establish truth or corpus completeness |
| Offline evaluation | evaluation command and checked-in corpus | deterministic metrics and case results | measures the declared corpus, not general quality |
| Retry and circuit breaking | `safeguards/` | bounded attempts, breaker state, typed failure | activated only when the caller composes it |
| Resource and cache policy | resource, memoization, and effect primitives | lifetime, cache, and failure records | host owns distributed transactions and retention |
| CLI and HTTP adapters | `interfaces/` | stable files, responses, exit/status semantics | HTTP default index state is process-local |

## Capability selection

- Use the document-oriented pipeline when structural deduplication and
  materialized observations are required.
- Use the lazy pipeline when streaming composition is the principal need and
  its narrower post-processing contract is acceptable.
- Use the local retrieval commands for bounded, inspectable applications and
  reference evaluation.
- Use `bijux-canon-index` when retrieval requires backend capability
  negotiation, governed execution, or replayable vector provenance.
- Supply explicit safeguards around external readers, models, stores, and
  effects; the core pipeline does not add hidden retry or cache semantics.

The [invariants](../quality/invariants.md) define the laws behind these
capabilities, and the [known limitations](../quality/known-limitations.md)
state where their guarantees end.
