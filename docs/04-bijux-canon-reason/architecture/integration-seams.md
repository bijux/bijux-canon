---
title: Integration Seams
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Integration Seams

Integration seams matter because `bijux-canon-reason` touches neighboring packages without becoming them. The handoff into and out of reasoning work should be explicit enough to survive review under change.

## What To Check

- name the seam where work enters from index, agent, and runtime
- name the seam where `bijux-canon-reason` hands responsibility outward again
- treat seam ambiguity as a design problem, not as a documentation gap only

## First Proof Check

- `src/bijux_canon_reason` and reasoning artifacts for the structural ownership boundary
- `tests` for claim, verification, and provenance evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-reason` needs hidden structure to defend claim formation, checks, and reasoning artifacts, the architecture is already too opaque.
