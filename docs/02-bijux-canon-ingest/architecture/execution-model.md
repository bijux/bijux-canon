---
title: Execution Model
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Execution Model

The execution model for `bijux-canon-ingest` should tell one clear story from raw source material to prepared handoff output. A reader should not need to reconstruct the main control path from filenames or logs.

## What To Check

- identify the entrypoints that start source preparation before retrieval begins
- identify the core work that transforms the flow from raw source material to prepared handoff output
- identify the exact handoff where ownership moves to a neighbor or to a caller-visible output

## First Proof Check

- `src/bijux_canon_ingest/processing`, `retrieval`, and `application` for the structural ownership boundary
- `tests` for deterministic preparation evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-ingest` needs hidden structure to defend source preparation before retrieval begins, the architecture is already too opaque.
