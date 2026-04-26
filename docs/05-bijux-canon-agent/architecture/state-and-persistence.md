---
title: State and Persistence
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# State and Persistence

State should exist in `bijux-canon-agent` only when it helps defend role coordination, workflow order, and traces. Persistence that cannot be tied to package ownership is usually hidden coupling rather than architecture.

## What To Check

- name the durable state that matters to this package role
- separate local working state from caller-visible or cross-package durable state
- treat unexplained persistence as a structural smell until its ownership is explicit

## First Proof Check

- `src/bijux_canon_agent` and tracked workflow surfaces for the structural ownership boundary
- `tests` for determinism and traceability evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-agent` needs hidden structure to defend role coordination, workflow order, and traces, the architecture is already too opaque.
