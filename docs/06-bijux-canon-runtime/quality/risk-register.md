---
title: Risk Register
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Risk Register

The risk register for `bijux-canon-runtime` should track the failures most likely to damage trust in governed run behavior. The goal is not alarmism; it is durable memory about the risks that matter.

## What To Check

- prioritize risks that would make readers trust acceptance, persistence, or replay that is weaker in practice than in prose
- keep risk language tied to current code, tests, and documentation surfaces
- treat repeated surprise failures as proof that a risk is not being tracked honestly enough

## First Proof Check

- `tests` and package-local validation surfaces for executable evidence
- caller-facing docs, limits, and risks for the trust story readers actually receive
- release notes and change records when the work alters what others may safely assume

## Bottom Line

If `bijux-canon-runtime` cannot explain why `governed run behavior` should be trusted after a change, the quality work is still incomplete.
