---
title: State and Persistence
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# State and Persistence

State should exist in `bijux-canon-runtime` only when it helps defend acceptance, persistence, replay, and governed execution. Persistence that cannot be tied to package ownership is usually hidden coupling rather than architecture.

## What To Check

- name the durable state that matters to this package role
- separate local working state from caller-visible or cross-package durable state
- treat unexplained persistence as a structural smell until its ownership is explicit

## First Proof Check

- `src/bijux_canon_runtime/application/execute_flow.py`, `model/`, and `observability/` for the structural ownership boundary
- `tests` for acceptance, replay, and persistence evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-runtime` needs hidden structure to defend acceptance, persistence, replay, and governed execution, the architecture is already too opaque.
