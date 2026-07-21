---
title: Operations
audience: mixed
type: index
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Operations

An ingest run is operationally complete only when its inputs, effective
configuration, prepared records, retrieval artifacts, and diagnostics can be
related to one another. Successful process exit alone does not establish that
the output is reproducible or suitable for citation.

## Operating lifecycle

```mermaid
flowchart LR
    inspect["inspect source and schema"]
    configure["resolve configuration"]
    prepare["prepare and validate records"]
    index["build and persist local index"]
    query["retrieve, ask, or evaluate"]
    retain["retain artifacts and diagnostics"]

    inspect --> configure --> prepare --> index --> query --> retain
    prepare -. invalid record .-> inspect
    index -. mismatched artifacts .-> prepare
    query -. weak citations .-> index
```

## Normal workflows

| Objective | Operational path | Evidence to retain |
| --- | --- | --- |
| Prepare documents | validate input, run the configured pipeline, inspect rejected and emitted rows | source identity, effective configuration, output CSV/JSONL, diagnostics |
| Build a local index | choose BM25 or cosine, build from the prepared chunk set, keep index and chunks together | index metadata, chunk file, embedding choice, package version |
| Retrieve candidates | load the paired artifact, run the query, inspect rank and score semantics | query, index identity, ordered chunk IDs and scores |
| Produce an answer | retrieve first, then construct an extractive response tied to chunk IDs | answer, citations, retrieved chunk set |
| Evaluate retrieval | run the evaluation command against declared expectations | evaluation input, metrics, configuration, index identity |
| Serve HTTP v1 | configure process resources, expose health, and account for process-local default state | deployment configuration, health evidence, logs, restart policy |

## Incident routing

| Symptom | Inspect first | Recovery principle |
| --- | --- | --- |
| Records changed between equivalent runs | source bytes, normalization settings, package version, identifier inputs | restore the exact inputs and configuration before rebuilding |
| Chunk offsets do not match source files | normalized text and cleaning stages | treat offsets as normalized-string positions; rebuild source mapping if required |
| Index loads but retrieval is incoherent | index/chunk pairing, algorithm, embedding configuration | restore the matched artifact set; do not mix generations |
| HTTP state disappears | worker topology and process restart | rebuild state or supply an application-owned durable store |
| Citations do not resolve | retrieved chunk set and answer construction | reject the answer and reproduce retrieval from the same index identity |
| Optional provider is unavailable | installed extra, credentials, network, adapter error | restore the explicit dependency; do not substitute silently |

## Deployment boundaries

The package supplies local persistence and a service adapter, not a production
control plane. Authentication, authorization, tenant isolation, encryption key
management, durable distributed storage, load balancing, and retention policy
belong to the deploying application. The deterministic hash embedding is safe
as a reproducible baseline but must not be represented as semantic retrieval.

## Operate by need

| Need | Guide |
| --- | --- |
| Install supported extras and verify entrypoints | [Installation and setup](installation-and-setup.md) |
| Work on the package locally | [Local development](local-development.md) |
| Run common preparation and retrieval journeys | [Common workflows](common-workflows.md) |
| Interpret logs, metrics, and run records | [Observability and diagnostics](observability-and-diagnostics.md) |
| Plan memory, corpus size, and concurrency | [Performance and scaling](performance-and-scaling.md) |
| Recover a failed run or inconsistent artifact | [Failure recovery](failure-recovery.md) |
| Assess security-sensitive deployment work | [Security and safety](security-and-safety.md) and [Deployment boundaries](deployment-boundaries.md) |
| Release a caller-visible change | [Release and versioning](release-and-versioning.md) |
