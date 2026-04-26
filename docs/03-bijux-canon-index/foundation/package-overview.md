---
title: Package Overview
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Package Overview

`bijux-canon-index` exists to make retrieval behavior explicit, replayable, and reviewable. It turns prepared ingest output into embeddings, index state, and retrieval results that downstream packages can inspect instead of merely trust.

## Role Model

```mermaid
flowchart LR
    prepared["prepared ingest output"]
    index["retrieval and indexing behavior"]
    results["replayable retrieval results"]
    downstream["reason, agent, and runtime consumers"]

    prepared --> index --> results --> downstream
```

This page should let a reader picture index as the package that owns retrieval
semantics in the open. The result is not just search output; it is search
behavior that later packages can replay, compare, and review.

## Boundary Verdict

If the work changes how search is executed, replayed, compared, or exposed as retrieval output, it belongs here. If it changes source preparation, claim meaning, or governed run policy, it does not.

## What This Package Makes Possible

- retrieval behavior becomes a named contract instead of an accidental consequence of backend code
- provenance and replay stay attached to search results that later packages rely on
- index-specific search assumptions stop leaking into reasoning and runtime layers

## Tempting Mistakes

- treating vector execution as infrastructure plumbing instead of package-owned behavior
- burying caller-facing retrieval differences inside plugins or backend adapters
- using runtime authority to paper over unclear retrieval semantics

## First Proof Check

- `packages/bijux-canon-index/src/bijux_canon_index` for retrieval ownership in code
- `packages/bijux-canon-index/apis` for tracked caller-facing schemas
- `packages/bijux-canon-index/tests` for replay and provenance evidence

## Design Pressure

The pressure on index is to keep retrieval logic visible enough that later
packages never need to guess what happened inside search. If retrieval policy
spills into adapters or downstream code, the package boundary stops paying off.
