---
title: Change Validation
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Change Validation

Change validation for `bijux-canon-runtime` should match the seam that actually moved. Strong validation means choosing evidence that tests the real risk around governed run behavior, not just adding more checks mechanically.

## What To Check

- match proof depth to the surface that changed: boundary, contract, artifact, or behavior
- update the surrounding docs when validation reveals a changed assumption
- treat low-signal validation as unfinished work when the change touches a high-trust surface

## First Proof Check

- `tests` and package-local validation surfaces for executable evidence
- caller-facing docs, limits, and risks for the trust story readers actually receive
- release notes and change records when the work alters what others may safely assume

## Bottom Line

If `bijux-canon-runtime` cannot explain why `governed run behavior` should be trusted after a change, the quality work is still incomplete.
