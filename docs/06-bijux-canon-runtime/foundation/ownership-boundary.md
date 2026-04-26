---
title: Ownership Boundary
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Ownership Boundary

`bijux-canon-runtime` owns governed execution authority above the lower package family. Use it when a behavior looks close enough to local execution below that runtime might absorb work it should merely govern.

## Use This Boundary Test

- keep the work here when it changes acceptance, persistence, replay, execution authority, or run governance
- move the work down when it changes package-local semantics in ingest, index, reason, or agent
- move the work out to maintenance when it changes repository-wide automation rather than runtime behavior itself

## Borderline Example

A new persistence acceptance rule belongs here. A new agent-specific retry policy does not, even if runtime observes the final result.

## First Proof Check

- `packages/bijux-canon-runtime/src` for the owned implementation boundary
- `packages/bijux-canon-runtime/tests` for proof that the boundary survives change
- neighboring handbook roots in agent and the lower canonical packages when the work still looks plausible elsewhere

## Bottom Line

A reviewer should be able to use this page to say not just why work belongs in `bijux-canon-runtime`, but why it does not belong in the nearest tempting neighbor.
