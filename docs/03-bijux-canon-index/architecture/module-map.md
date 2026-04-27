---
title: Module Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Module Map

The module map for `bijux-canon-index` should connect a question about index work to the code area that owns it. If a reviewer cannot point to the owning module for retrieval execution, replay, and provenance, the structure is already too implicit.

## What To Check

- the main ownership boundary is `src/bijux_canon_index` and `apis`
- the map should separate retrieval execution, replay, and provenance from neighboring concerns in ingest, reason, and runtime
- the first proof check is `tests` for replay and provenance evidence aligned with the same structure

## First Proof Check

- `src/bijux_canon_index` and `apis` for the structural ownership boundary
- `tests` for replay and provenance evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-index` needs hidden structure to defend retrieval execution, replay, and provenance, the architecture is already too opaque.
