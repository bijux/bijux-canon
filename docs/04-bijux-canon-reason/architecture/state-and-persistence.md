---
title: State and Persistence
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# State and Persistence

State should exist in `bijux-canon-reason` only when it helps defend claim formation, checks, and reasoning artifacts. Persistence that cannot be tied to package ownership is usually hidden coupling rather than architecture.

## What To Check

- name the durable state that matters to this package role
- separate local working state from caller-visible or cross-package durable state
- treat unexplained persistence as a structural smell until its ownership is explicit

## First Proof Check

- `src/bijux_canon_reason` and reasoning artifacts for the structural ownership boundary
- `tests` for claim, verification, and provenance evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-reason` needs hidden structure to defend claim formation, checks, and reasoning artifacts, the architecture is already too opaque.
