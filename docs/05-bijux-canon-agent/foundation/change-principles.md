---
title: Change Principles
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Change Principles

Changes in `bijux-canon-agent` should make workflows easier to trace, easier to explain, or less likely to smuggle in hidden policy. If a change makes orchestration more surprising, it is probably a regression.

## Change Rules

- prefer changes that strengthen determinism, trace quality, and explicit role boundaries
- update artifacts, examples, and tests when caller-visible workflow behavior changes
- reject changes that move reasoning or runtime authority into orchestration for convenience

## Stop Rule

Stop the change if a reviewer can no longer reconstruct what happened from the documented traces.

## Bottom Line

A good change leaves the package easier to defend after the diff than before it.
