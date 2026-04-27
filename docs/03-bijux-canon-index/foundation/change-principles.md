---
title: Change Principles
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Change Principles

Changes in `bijux-canon-index` should make retrieval behavior easier to explain, easier to replay, or easier to trust. If a change makes search more opaque, it is moving in the wrong direction.

## Change Rules

- prefer changes that improve replay, provenance, and explicit retrieval contracts
- update schemas, examples, and tests when caller-visible search behavior changes
- reject changes that hide search semantics inside adapters or downstream assumptions

## Stop Rule

Stop the change if the best explanation is “the backend works that way.”

## Bottom Line

A good change leaves the package easier to defend after the diff than before it.
