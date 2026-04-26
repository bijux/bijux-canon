---
title: Error Model
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Error Model

The error model for `bijux-canon-index` should reveal how the package fails when retrieval execution, replay, and provenance goes wrong. Hidden failure semantics make later layers absorb problems they did not create.

## What To Check

- name the failures that belong to this package role
- separate local failure handling from failures that must cross a package seam
- treat recovery shortcuts that hide ownership as design debt

## First Proof Check

- `src/bijux_canon_index` and `apis` for the structural ownership boundary
- `tests` for replay and provenance evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-index` needs hidden structure to defend retrieval execution, replay, and provenance, the architecture is already too opaque.
