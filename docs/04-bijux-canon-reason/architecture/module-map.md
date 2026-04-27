---
title: Module Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Module Map

The module map for `bijux-canon-reason` should connect a question about reasoning work to the code area that owns it. If a reviewer cannot point to the owning module for claim formation, checks, and reasoning artifacts, the structure is already too implicit.

## What To Check

- the main ownership boundary is `src/bijux_canon_reason` and reasoning artifacts
- the map should separate claim formation, checks, and reasoning artifacts from neighboring concerns in index, agent, and runtime
- the first proof check is `tests` for claim, verification, and provenance evidence aligned with the same structure

## First Proof Check

- `src/bijux_canon_reason` and reasoning artifacts for the structural ownership boundary
- `tests` for claim, verification, and provenance evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-reason` needs hidden structure to defend claim formation, checks, and reasoning artifacts, the architecture is already too opaque.
