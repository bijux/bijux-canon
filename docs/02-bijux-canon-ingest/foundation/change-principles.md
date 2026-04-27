---
title: Change Principles
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Change Principles

Changes in `bijux-canon-ingest` should make prepared input easier to explain, easier to verify, or harder to misuse. Anything else is likely noise, drift, or boundary creep.

## Change Rules

- tighten preparation logic when it removes ambiguity visible to downstream packages
- change docs, artifacts, and tests in the same series when package behavior changes
- reject changes that enlarge ingest only because a neighbor would rather not own its own complexity

## Stop Rule

Stop the change if the best argument for it is that ingest is “close enough.”

## Bottom Line

A good change leaves the package easier to defend after the diff than before it.
