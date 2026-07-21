---
title: Ingest Handbook
audience: mixed
type: index
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Ingest Handbook

`bijux-canon-ingest` turns source documents into deterministic records, chunks,
local retrieval indexes, ranked candidates, and extractive answers with
citations. It supports both small in-process transformations and file-backed
pipelines without making HTTP, CLI, or orchestration dependencies mandatory at
package import time.

Ingest owns uncertainty in source shape. Invalid chunk geometry, malformed CSV
rows, unsafe filtering rules, retry exhaustion, and circuit-breaker decisions
remain explicit results rather than becoming silent changes to downstream
evidence.

```mermaid
flowchart LR
    csv["CSV or RawDoc stream"]
    rules["safe rules + CleanConfig"]
    clean["CleanDoc"]
    chunks["ChunkWithoutEmbedding"]
    index["BM25 or NumPy cosine index"]
    result["candidates or cited answer"]

    csv --> rules --> clean --> chunks --> index --> result
    rules -. typed ErrInfo .-> result
```

## Available Surfaces

| Surface | Concrete operations | Stable evidence |
| --- | --- | --- |
| Python root | `RawDoc`, `CleanDoc`, `RagEnv`, `clean_doc`, `chunk_doc`, streaming combinators, `Result`, retry and breaker helpers | `__all__`, API-freeze tests, typed marker |
| command | CSV pipeline; `index build`; `retrieve`; `ask`; `eval` | parser tests and end-to-end fixtures |
| HTTP v1 | health, chunk, index build, retrieve, ask | `apis/bijux-canon-ingest/v1/schema.yaml` |
| storage | CSV document input, JSONL chunk output, persisted BM25 or NumPy-cosine index | adapter and round-trip tests |

The package-local index and extractive-answer features support an ingest-owned
workflow. `bijux-canon-index` remains the owner of declared vector execution,
backend capability negotiation, provenance-rich execution artifacts, and
replay comparison across vector backends.

## Follow One Prepared Document

| Boundary | Retained evidence | Review question |
| --- | --- | --- |
| parse | source identifier, input fields, adapter result | were the intended bytes accepted without silent coercion? |
| clean | `CleanConfig`, normalized text, safeguard outcome | which rules changed the source and which content was refused? |
| chunk | chunk geometry, parent identity, offsets, chunk records | can every chunk be traced to its exact prepared parent? |
| persist | JSONL records or local index manifest | can a later process load the same prepared material? |
| retrieve | query, index identity, ranked candidates, citations | which ingest-local records produced this extractive answer? |

The first reviewable result is not the answer text. It is the chain from source
identity through configuration and chunk offsets to ranked records. The
[entrypoint examples](interfaces/entrypoints-and-examples.md) show the Python,
CSV, local-index, and HTTP forms of that chain.

## Boundary With Index

Ingest owns preparation and its dependency-light BM25 or NumPy-cosine local
workflow. Index owns declared vector execution across backend capabilities,
budgets, provenance-rich execution artifacts, and replay comparison. Move the
question to index when backend selection, approximation, vector execution, or
cross-backend comparison becomes the disputed decision.

```text
source bytes -> ingest records and chunks -> index execution request
```

Reason, agent, and runtime may consume ingest artifacts. They must not repair
missing source identity, invent chunk provenance, or reinterpret a preparation
failure as empty evidence.

## Evidence And Limits

| Claim | Evidence to inspect | Limit |
| --- | --- | --- |
| cleaning is deterministic | input identity, normalized configuration, output record, repeated serialization | does not prove source truth |
| a chunk is traceable | parent identity, offsets, text, stable record shape | depends on retaining the prepared parent |
| local retrieval is reproducible | index type and identity, corpus records, query, ranking output | applies to the ingest-local backend, not every vector backend |
| an extractive answer is cited | candidate records and cited spans | does not establish that the corpus is complete |
| bulk processing handled failure honestly | policy, typed `ErrInfo`, stage context, error counts | collected errors still require caller disposition |

## Continue By Question

| Question | Next page |
| --- | --- |
| what belongs inside the preparation boundary? | [Foundation](foundation/index.md) |
| how do processing, application, and adapters depend on one another? | [Architecture](architecture/index.md) |
| which Python, CLI, HTTP, and storage contracts are callable? | [Interfaces](interfaces/index.md) |
| how do I install, run, diagnose, or recover a pipeline? | [Operations](operations/index.md) |
| what evidence protects deterministic preparation? | [Quality](quality/index.md) |

## Failure Boundaries

- parsing and configuration failures identify the invalid input or override
- transformation failures use typed `ErrInfo` values and retain stage context
- bulk processing can fail fast, collect errors, cap errors, or stop at an
  explicit error-rate threshold
- retries, circuit breakers, resource guards, and caches are separate policies;
  enabling one does not silently imply another
- optional YAML, Typer, NumPy, sentence-transformer, and HTTP integrations are
  loaded at their owning boundary rather than on a dependency-light root import
