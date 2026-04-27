---
title: Execution Model
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Execution Model

The execution model for `bijux-canon-index` should tell one clear story from prepared input to retrieval output. A reader should not need to reconstruct the main control path from filenames or logs.

## What To Check

- identify the entrypoints that start retrieval execution, replay, and provenance
- identify the core work that transforms the flow from prepared input to retrieval output
- identify the exact handoff where ownership moves to a neighbor or to a caller-visible output

## First Proof Check

- `src/bijux_canon_index` and `apis` for the structural ownership boundary
- `tests` for replay and provenance evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-index` needs hidden structure to defend retrieval execution, replay, and provenance, the architecture is already too opaque.
