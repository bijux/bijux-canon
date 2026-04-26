---
title: Ownership Boundary
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Ownership Boundary

`bijux-canon-reason` owns the moment where evidence becomes a claim, check, or reasoning artifact. Use it when policy could easily be hidden in retrieval output below or workflow code above.

## Use This Boundary Test

- keep the work here when it changes claim formation, verification, provenance interpretation, or reasoning artifacts
- move the work down to `bijux-canon-index` when it changes how evidence is fetched or replayed
- move the work upward when it changes multi-step coordination or final run authority

## Borderline Example

A new verification rule belongs here. A new workflow rule for when verification should run belongs in agent.

## First Proof Check

- `packages/bijux-canon-reason/src` for the owned implementation boundary
- `packages/bijux-canon-reason/tests` for proof that the boundary survives change
- neighboring handbook roots in index, agent, and runtime when the work still looks plausible elsewhere

## Bottom Line

A reviewer should be able to use this page to say not just why work belongs in `bijux-canon-reason`, but why it does not belong in the nearest tempting neighbor.
