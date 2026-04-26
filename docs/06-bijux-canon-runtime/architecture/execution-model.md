---
title: Execution Model
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Execution Model

The execution model for `bijux-canon-runtime` should tell one clear story from lower-package output to governed run artifact. A reader should not need to reconstruct the main control path from filenames or logs.

## What To Check

- identify the entrypoints that start acceptance, persistence, replay, and governed execution
- identify the core work that transforms the flow from lower-package output to governed run artifact
- identify the exact handoff where ownership moves to a neighbor or to a caller-visible output

## First Proof Check

- `src/bijux_canon_runtime/application/execute_flow.py`, `model/`, and `observability/` for the structural ownership boundary
- `tests` for acceptance, replay, and persistence evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-runtime` needs hidden structure to defend acceptance, persistence, replay, and governed execution, the architecture is already too opaque.
