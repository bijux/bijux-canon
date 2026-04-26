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

## Bottom Line

If `bijux-canon-index` grows in a way that weakens this argument, the package is getting larger without getting clearer.
