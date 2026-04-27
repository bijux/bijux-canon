---
title: Dependency Direction
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Dependency Direction

Dependency direction matters because `bijux-canon-agent` should make role coordination, workflow order, and traces easier to explain, not harder. Imported convenience must not reverse the ownership logic of the package.

## What To Check

- dependencies should point toward supporting role coordination, workflow order, and traces, not toward re-owning neighbor behavior
- upstream and downstream seams should stay legible across workflow input to trace-backed coordinated output
- if the direction only makes sense after a long verbal explanation, the structure is already drifting

## First Proof Check

- `src/bijux_canon_agent` and tracked workflow surfaces for the structural ownership boundary
- `tests` for determinism and traceability evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-agent` needs hidden structure to defend role coordination, workflow order, and traces, the architecture is already too opaque.
