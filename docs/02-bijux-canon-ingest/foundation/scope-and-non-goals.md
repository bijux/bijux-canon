---
title: Scope and Non-Goals
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Scope and Non-Goals

`bijux-canon-ingest` owns deterministic preparation of document material and a
compact local retrieval path built over the prepared records. It makes source
transformation, chunk identity, local ranking, and extractive citation visible;
it does not own platform-wide retrieval governance or interpretive authority.

```mermaid
flowchart LR
    source["source rows and text"]
    preparation["normalize, identify, chunk, embed"]
    local["local index, retrieve, ask, evaluate"]
    handoff["prepared records + cited candidates"]
    platform["governed index / reasoning / runtime"]

    source --> preparation --> local --> handoff --> platform
```

## In scope

- strict records for raw documents, cleaned documents, chunk spans,
  embeddings, errors, and observations;
- deterministic filtering, normalization, chunking, tail policy, structural
  deduplication, and reference embeddings;
- lazy and materialized pipeline composition, result folds, streaming,
  scheduling, and explicit effect boundaries;
- local BM25 and NumPy cosine indexes, ranked retrieval, extractive answers,
  citations, and offline evaluation;
- CSV, JSONL, MessagePack, CLI, Python, and HTTP adapter contracts;
- opt-in retry, circuit breaker, cache, resource, rule, and telemetry
  primitives for callers composing external work.

## Non-goals

| Not owned here | Owning boundary |
| --- | --- |
| Source truth, licensing, safety, or authority | source-governance process supplied by the application |
| Semantic quality of an embedding model | selected model and its evaluation evidence |
| Cross-backend capability negotiation and governed vector replay | `bijux-canon-index` |
| Whether a retrieved passage supports a claim | `bijux-canon-reason` |
| Role scheduling, convergence, and agent traces | `bijux-canon-agent` |
| Run acceptance, durable workflow authority, and policy replay | `bijux-canon-runtime` |
| Authentication, tenant isolation, distributed storage, or queue semantics | deploying system |

## Important distinctions

The in-package retrieval implementation is intentional. It provides a local,
inspectable document-to-answer path and deterministic evaluation baseline. It
does not replace the index package's execution artifacts, backend capability
contracts, or replay policy.

The document-oriented and lazy pipelines also have different contracts. The
document pipeline materializes observations and performs structural
deduplication; the minimal lazy path does not promise identical
post-processing. Callers choose the behavior explicitly.

## Scope test

A change belongs here when its primary invariant concerns how a source becomes
an addressable prepared or locally retrievable record. If the primary question
is what a ranking guarantees across backends, what evidence means, which role
runs, or whether a complete run is accepted, the change belongs at the next
authority boundary.

See the [capability map](capability-map.md) for implemented surfaces and
[known limitations](../quality/known-limitations.md) for the guarantees they do
not provide.
