---
title: Risk Register
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Risk Register

The risk register for `bijux-canon-index` should track the failures most likely to damage trust in retrieval and replay behavior. The goal is not alarmism; it is durable memory about the risks that matter.

## What To Check

- prioritize risks that would make callers trust search or replay behavior that has drifted
- keep risk language tied to current code, tests, and documentation surfaces
- treat repeated surprise failures as proof that a risk is not being tracked honestly enough

## First Proof Check

- `tests` and package-local validation surfaces for executable evidence
- caller-facing docs, limits, and risks for the trust story readers actually receive
- release notes and change records when the work alters what others may safely assume

## Bottom Line

If `bijux-canon-index` cannot explain why `retrieval and replay behavior` should be trusted after a change, the quality work is still incomplete.
