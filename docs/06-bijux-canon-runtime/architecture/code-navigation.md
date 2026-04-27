---
title: Code Navigation
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Code Navigation

Code navigation should shorten the path from a runtime authority question to the owning files in `bijux-canon-runtime`. If readers still need exploratory digging, the navigation story is not specific enough.

## What To Check

- start with `src/bijux_canon_runtime/application/execute_flow.py`, `model/`, and `observability/` for the main ownership seam
- follow with `tests` for acceptance, replay, and persistence evidence when the question is whether the code still matches the structure
- treat wide, unfocused navigation advice as a sign that the structure is not yet legible enough

## First Proof Check

- `src/bijux_canon_runtime/application/execute_flow.py`, `model/`, and `observability/` for the structural ownership boundary
- `tests` for acceptance, replay, and persistence evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-runtime` needs hidden structure to defend acceptance, persistence, replay, and governed execution, the architecture is already too opaque.
