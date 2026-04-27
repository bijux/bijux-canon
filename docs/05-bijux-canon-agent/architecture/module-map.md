---
title: Module Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Module Map

The module map for `bijux-canon-agent` should connect a question about agent orchestration work to the code area that owns it. If a reviewer cannot point to the owning module for role coordination, workflow order, and traces, the structure is already too implicit.

## What To Check

- the main ownership boundary is `src/bijux_canon_agent` and tracked workflow surfaces
- the map should separate role coordination, workflow order, and traces from neighboring concerns in reason and runtime
- the first proof check is `tests` for determinism and traceability evidence aligned with the same structure

## First Proof Check

- `src/bijux_canon_agent` and tracked workflow surfaces for the structural ownership boundary
- `tests` for determinism and traceability evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-agent` needs hidden structure to defend role coordination, workflow order, and traces, the architecture is already too opaque.
