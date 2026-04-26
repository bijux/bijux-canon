---
title: Integration Seams
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Integration Seams

Integration seams matter because `bijux-canon-ingest` touches neighboring packages without becoming them. The handoff into and out of ingest work should be explicit enough to survive review under change.

## What To Check

- name the seam where work enters from index, reason, agent, and runtime
- name the seam where `bijux-canon-ingest` hands responsibility outward again
- treat seam ambiguity as a design problem, not as a documentation gap only

## First Proof Check

- `src/bijux_canon_ingest/processing`, `retrieval`, and `application` for the structural ownership boundary
- `tests` for deterministic preparation evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-ingest` needs hidden structure to defend source preparation before retrieval begins, the architecture is already too opaque.
