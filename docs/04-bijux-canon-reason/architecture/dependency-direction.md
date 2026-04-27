---
title: Dependency Direction
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Dependency Direction

Dependency direction matters because `bijux-canon-reason` should make claim formation, checks, and reasoning artifacts easier to explain, not harder. Imported convenience must not reverse the ownership logic of the package.

## What To Check

- dependencies should point toward supporting claim formation, checks, and reasoning artifacts, not toward re-owning neighbor behavior
- upstream and downstream seams should stay legible across evidence input to inspectable reasoning output
- if the direction only makes sense after a long verbal explanation, the structure is already drifting

## First Proof Check

- `src/bijux_canon_reason` and reasoning artifacts for the structural ownership boundary
- `tests` for claim, verification, and provenance evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-reason` needs hidden structure to defend claim formation, checks, and reasoning artifacts, the architecture is already too opaque.
