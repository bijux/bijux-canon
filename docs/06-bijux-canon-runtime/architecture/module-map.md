---
title: Module Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Module Map

The module map for `bijux-canon-runtime` should connect a question about runtime authority work to the code area that owns it. If a reviewer cannot point to the owning module for acceptance, persistence, replay, and governed execution, the structure is already too implicit.

## What To Check

- the main ownership boundary is `src/bijux_canon_runtime/application/execute_flow.py`, `model/`, and `observability/`
- the map should separate acceptance, persistence, replay, and governed execution from neighboring concerns in the lower canonical packages and maintenance surfaces
- the first proof check is `tests` for acceptance, replay, and persistence evidence aligned with the same structure

## First Proof Check

- `src/bijux_canon_runtime/application/execute_flow.py`, `model/`, and `observability/` for the structural ownership boundary
- `tests` for acceptance, replay, and persistence evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-runtime` needs hidden structure to defend acceptance, persistence, replay, and governed execution, the architecture is already too opaque.
