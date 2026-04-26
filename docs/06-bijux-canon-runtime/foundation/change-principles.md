---
title: Change Principles
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Change Principles

Changes in `bijux-canon-runtime` should make governed runs easier to justify, easier to replay, or harder to misinterpret. If a change makes authority more implicit, it is a regression even when it works.

## Change Rules

- prefer changes that strengthen explicit acceptance and replay policy
- update artifacts, diagnostics, and tests when governed run behavior changes
- reject changes that turn runtime into a holding area for unrelated late-stage logic

## Stop Rule

Stop the change if runtime is becoming broader without making authority easier to defend.

## Bottom Line

A good change leaves the package easier to defend after the diff than before it.
