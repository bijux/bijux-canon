---
title: Dependency Direction
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Dependency Direction

Dependency direction matters because `bijux-canon-index` should make retrieval execution, replay, and provenance easier to explain, not harder. Imported convenience must not reverse the ownership logic of the package.

## What To Check

- dependencies should point toward supporting retrieval execution, replay, and provenance, not toward re-owning neighbor behavior
- upstream and downstream seams should stay legible across prepared input to retrieval output
- if the direction only makes sense after a long verbal explanation, the structure is already drifting

## First Proof Check

- `src/bijux_canon_index` and `apis` for the structural ownership boundary
- `tests` for replay and provenance evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-index` needs hidden structure to defend retrieval execution, replay, and provenance, the architecture is already too opaque.
