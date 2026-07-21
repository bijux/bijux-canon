---
title: Preparation Review
audience: mixed
type: how-to
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Preparation Review

Review follows the data from source identity to downstream handoff. Begin at
the changed invariant, then inspect every serialization or execution boundary
the value crosses.

```mermaid
flowchart TD
    input[Source and configuration]
    transform[Filter, clean, chunk]
    execute[Embed and schedule]
    retain[Persist records and observations]
    consume[Index, retrieve, cite]

    input --> transform --> execute --> retain --> consume
```

## Identity and transformation

- Is document identity derived before transformations that could erase source
  distinctions?
- Do normalization, chunk size, overlap, and tail policy participate in the
  retained configuration?
- Are spans interpreted against normalized text, and can every retained span
  be resolved?
- Does a change to identity or ordering include comparison against the prior
  behavior rather than only new happy-path fixtures?

## Execution and failure

- Does lazy execution preserve order, bounded buffering, termination, and
  backpressure?
- Are retries, breakers, caches, and resource lifetimes explicit at the point
  where they change behavior?
- Can partial failure be distinguished from an empty successful corpus?
- Do injected readers, cleaners, embedders, stores, and clocks have recorded
  identity when reproducibility depends on them?

## Public and persisted boundaries

- Do strict models reject unknown fields and incompatible vector dimensions?
- Do CLI and HTTP adapters preserve typed error meaning and nonzero failure
  status?
- Does persisted state reject incompatible formats and stale configuration?
- Are secrets, sensitive source text, and unbounded samples absent from logs
  and diagnostics?

## Retrieval interpretation

- Is the hash embedder described only as a deterministic baseline?
- Does a quality claim name its corpus, model profile, metrics, and threshold?
- Do citations retain chunk identity and resolvable span data?
- Is governed backend selection and replay left to `bijux-canon-index` rather
  than absorbed into ingest?

A review is complete when the evidence explains both accepted material and
rejected material. Route the result through [release acceptance](definition-of-done.md)
and check unresolved exposure in [known limitations](known-limitations.md).
