---
title: Module Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Module Map

The module map for `bijux-canon-ingest` should connect a question about ingest work to the code area that owns it. If a reviewer cannot point to the owning module for source preparation before retrieval begins, the structure is already too implicit.

## What To Check

- the main ownership boundary is `src/bijux_canon_ingest/processing`, `retrieval`, and `application`
- the map should separate source preparation before retrieval begins from neighboring concerns in index, reason, agent, and runtime
- the first proof check is `tests` for deterministic preparation evidence aligned with the same structure

## First Proof Check

- `src/bijux_canon_ingest/processing`, `retrieval`, and `application` for the structural ownership boundary
- `tests` for deterministic preparation evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-ingest` needs hidden structure to defend source preparation before retrieval begins, the architecture is already too opaque.
