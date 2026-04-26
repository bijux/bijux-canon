---
title: Integration Seams
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Integration Seams

Integration seams matter because `bijux-canon-agent` touches neighboring packages without becoming them. The handoff into and out of agent orchestration work should be explicit enough to survive review under change.

## What To Check

- name the seam where work enters from reason and runtime
- name the seam where `bijux-canon-agent` hands responsibility outward again
- treat seam ambiguity as a design problem, not as a documentation gap only

## First Proof Check

- `src/bijux_canon_agent` and tracked workflow surfaces for the structural ownership boundary
- `tests` for determinism and traceability evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-agent` needs hidden structure to defend role coordination, workflow order, and traces, the architecture is already too opaque.
