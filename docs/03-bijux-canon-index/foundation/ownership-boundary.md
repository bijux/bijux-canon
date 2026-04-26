---
title: Ownership Boundary
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Ownership Boundary

`bijux-canon-index` owns retrieval behavior after ingest has already prepared the material. Use it when search logic looks close enough to either preprocessing below or reasoning above to blur the package seam.

## Use This Boundary Test

- keep the work here when it changes embedding, indexing, retrieval, provenance, or replay behavior
- move the work down to `bijux-canon-ingest` when the change is really about preparing source material before search
- move the work upward when the issue is about claim meaning, workflow policy, or governed run acceptance

## Borderline Example

A new retrieval comparator belongs here. A new rule for how a claim should interpret retrieved evidence belongs in reasoning instead.

## First Proof Check

- `packages/bijux-canon-index/src` for the owned implementation boundary
- `packages/bijux-canon-index/tests` for proof that the boundary survives change
- neighboring handbook roots in ingest, reason, and runtime when the work still looks plausible elsewhere

## Bottom Line

A reviewer should be able to use this page to say not just why work belongs in `bijux-canon-index`, but why it does not belong in the nearest tempting neighbor.
