---
title: Error Model
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Error Model

The error model for `bijux-canon-runtime` should reveal how the package fails when acceptance, persistence, replay, and governed execution goes wrong. Hidden failure semantics make later layers absorb problems they did not create.

## What To Check

- name the failures that belong to this package role
- separate local failure handling from failures that must cross a package seam
- treat recovery shortcuts that hide ownership as design debt

## First Proof Check

- `src/bijux_canon_runtime/application/execute_flow.py`, `model/`, and `observability/` for the structural ownership boundary
- `tests` for acceptance, replay, and persistence evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-runtime` needs hidden structure to defend acceptance, persistence, replay, and governed execution, the architecture is already too opaque.
