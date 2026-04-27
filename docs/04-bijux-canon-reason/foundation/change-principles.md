---
title: Change Principles
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Change Principles

Changes in `bijux-canon-reason` should make conclusions easier to inspect, easier to verify, or easier to challenge honestly. If a change adds cleverness without clarity, it is regressively opaque.

## Change Rules

- prefer changes that strengthen explicit claim, verification, and provenance behavior
- update artifacts, examples, and tests when reviewer-visible reasoning behavior changes
- reject changes that push meaning into retrieval or orchestration just to reduce local code

## Stop Rule

Stop the change if the claim logic becomes harder to explain after the edit.

## Bottom Line

A good change leaves the package easier to defend after the diff than before it.
