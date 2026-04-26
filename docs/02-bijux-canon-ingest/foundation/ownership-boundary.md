---
title: Ownership Boundary
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Ownership Boundary

`bijux-canon-ingest` owns the part of the system that makes source material predictable before retrieval begins. Use it when a change looks plausible here and somewhere else at the same time.

## Use This Boundary Test

- keep the work here when it removes ambiguity from source material before any search or reasoning step starts
- move the work to `bijux-canon-index` when it changes retrieval execution, vector behavior, or replay semantics
- move the work upward when it changes claim meaning, workflow coordination, or run acceptance policy

## Borderline Example

A parser tweak that stabilizes chunk boundaries belongs here. A tweak that changes retrieval ranking because chunk shape happened to expose the problem does not.

## First Proof Check

- `packages/bijux-canon-ingest/src` for the owned implementation boundary
- `packages/bijux-canon-ingest/tests` for proof that the boundary survives change
- neighboring handbook roots in index, reason, agent, and runtime when the work still looks plausible elsewhere

## Bottom Line

A reviewer should be able to use this page to say not just why work belongs in `bijux-canon-ingest`, but why it does not belong in the nearest tempting neighbor.
