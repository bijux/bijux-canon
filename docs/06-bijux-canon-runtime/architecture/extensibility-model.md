---
title: Extensibility Model
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Extensibility Model

Extensibility only helps when it preserves the core package argument. In `bijux-canon-runtime`, extension points should widen acceptance, persistence, replay, and governed execution intentionally rather than invite neighboring concerns in through convenience hooks.

## What To Check

- name the extension points that are safe because they preserve the package role
- name the boundaries that extensions must not cross
- prefer extension seams that keep review pressure visible in code and tests

## First Proof Check

- `src/bijux_canon_runtime/application/execute_flow.py`, `model/`, and `observability/` for the structural ownership boundary
- `tests` for acceptance, replay, and persistence evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-runtime` needs hidden structure to defend acceptance, persistence, replay, and governed execution, the architecture is already too opaque.
