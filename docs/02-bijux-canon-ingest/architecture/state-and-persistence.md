---
title: State and Persistence
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# State and Persistence

State should exist in `bijux-canon-ingest` only when it helps defend source preparation before retrieval begins. Persistence that cannot be tied to package ownership is usually hidden coupling rather than architecture.

## What To Check

- name the durable state that matters to this package role
- separate local working state from caller-visible or cross-package durable state
- treat unexplained persistence as a structural smell until its ownership is explicit

## First Proof Check

- `src/bijux_canon_ingest/processing`, `retrieval`, and `application` for the structural ownership boundary
- `tests` for deterministic preparation evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-ingest` needs hidden structure to defend source preparation before retrieval begins, the architecture is already too opaque.
