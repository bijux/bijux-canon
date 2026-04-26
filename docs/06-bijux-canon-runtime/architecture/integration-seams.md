---
title: Integration Seams
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Integration Seams

Integration seams matter because `bijux-canon-runtime` touches neighboring packages without becoming them. The handoff into and out of runtime authority work should be explicit enough to survive review under change.

## What To Check

- name the seam where work enters from the lower canonical packages and maintenance surfaces
- name the seam where `bijux-canon-runtime` hands responsibility outward again
- treat seam ambiguity as a design problem, not as a documentation gap only

## First Proof Check

- `src/bijux_canon_runtime/application/execute_flow.py`, `model/`, and `observability/` for the structural ownership boundary
- `tests` for acceptance, replay, and persistence evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-runtime` needs hidden structure to defend acceptance, persistence, replay, and governed execution, the architecture is already too opaque.
