---
title: Integration Seams
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Integration Seams

Integration seams matter because `bijux-canon-index` touches neighboring packages without becoming them. The handoff into and out of index work should be explicit enough to survive review under change.

## What To Check

- name the seam where work enters from ingest, reason, and runtime
- name the seam where `bijux-canon-index` hands responsibility outward again
- treat seam ambiguity as a design problem, not as a documentation gap only

## First Proof Check

- `src/bijux_canon_index` and `apis` for the structural ownership boundary
- `tests` for replay and provenance evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-index` needs hidden structure to defend retrieval execution, replay, and provenance, the architecture is already too opaque.
