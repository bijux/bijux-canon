---
title: Dependency Direction
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Dependency Direction

Dependency direction matters because `bijux-canon-runtime` should make acceptance, persistence, replay, and governed execution easier to explain, not harder. Imported convenience must not reverse the ownership logic of the package.

## What To Check

- dependencies should point toward supporting acceptance, persistence, replay, and governed execution, not toward re-owning neighbor behavior
- upstream and downstream seams should stay legible across lower-package output to governed run artifact
- if the direction only makes sense after a long verbal explanation, the structure is already drifting

## First Proof Check

- `src/bijux_canon_runtime/application/execute_flow.py`, `model/`, and `observability/` for the structural ownership boundary
- `tests` for acceptance, replay, and persistence evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-runtime` needs hidden structure to defend acceptance, persistence, replay, and governed execution, the architecture is already too opaque.
