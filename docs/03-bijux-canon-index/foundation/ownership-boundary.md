---
title: Ownership Boundary
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-07-21
---

# Ownership Boundary

Index authority is execution-contract authority over vectors. It binds a
request and immutable artifact to an eligible backend, records what happened,
and evaluates later replay without claiming what the result means.

```mermaid
flowchart TD
    change{"Which guarantee changes?"}
    prepare["document or chunk representation"]
    execute["vector contract, backend, rank, replay"]
    support["claim support and reasoning verification"]
    roles["role lifecycle and convergence"]
    flow["flow acceptance and tenant authority"]

    change --> prepare --> ingest["ingest"]
    change --> execute --> index["index"]
    change --> support --> reason["reason"]
    change --> roles --> agent["agent"]
    change --> flow --> runtime["runtime"]
```

## Decision table

| Change | Owner | Reason |
| --- | --- | --- |
| change normalization or chunk overlap | ingest | changes prepared content and identity |
| change stable tie-breaking or metric semantics | index | changes governed ranking behavior |
| add an ANN parameter to plan identity and replay comparison | index | changes approximation and provenance contract |
| decide whether a passage entails a proposed statement | reason | changes support interpretation |
| run a verifier role again after a veto | agent | changes workflow progression |
| accept bounded replay for a complete tenant flow | runtime | changes final workflow authority |

## Ingest and index retrieval

Ingest supplies a compact local BM25/NumPy path for document preparation,
evaluation, and extractive citation. Index becomes the owner when retrieval
requires an immutable execution artifact, explicit exact/ANN contract,
capability-selected backend, governed budget, cross-run provenance, or replay
comparison.

The handoff should retain document, chunk, vector, embedding/configuration, and
corpus identity. Index must not silently clean or rechunk input to satisfy a
backend; doing so would make artifact identity dishonest.

## Index and reason evidence

Index can explain why a result occupied a rank by joining its query, vector,
metric, score, backend, artifact, and execution. Reason decides whether the
retrieved content supports a claim. A result explanation is necessary
provenance, but it is not claim verification.

## Ownership test

Ask which record must change for the behavior to become correct. If it is a
prepared document or chunk, use ingest. If it is an execution request,
artifact, backend capability, score, run record, or replay comparison, use
index. If it is a support reference or verification finding, use reason.
