---
title: Extensibility Model
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Extensibility Model

Extensibility only helps when it preserves the core package argument. In `bijux-canon-ingest`, extension points should widen source preparation before retrieval begins intentionally rather than invite neighboring concerns in through convenience hooks.

## What To Check

- name the extension points that are safe because they preserve the package role
- name the boundaries that extensions must not cross
- prefer extension seams that keep review pressure visible in code and tests

## First Proof Check

- `src/bijux_canon_ingest/processing`, `retrieval`, and `application` for the structural ownership boundary
- `tests` for deterministic preparation evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-ingest` needs hidden structure to defend source preparation before retrieval begins, the architecture is already too opaque.
