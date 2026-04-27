---
title: Failure Recovery
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Failure Recovery

Failure recovery for `bijux-canon-agent` starts by stabilizing evidence around workflow and trace behavior before attempting a fix. Recovery should narrow the problem quickly instead of encouraging random retries.

## What To Check

- start with the artifacts and outputs that expose failure: workflow traces, role outputs, and agent diagnostics
- identify the first reproducible path before changing code or environment
- treat unrecoverable-from-docs incidents as proof that the runbook still has gaps

## First Proof Check

- `pyproject.toml`, `README.md`, and boundary-facing entrypoints for checked-in operating truth
- `tests` and runnable workflows for executable confirmation that the runbook still works
- release notes and version metadata when the work changes caller expectations

## Bottom Line

If `bijux-canon-agent` cannot be operated repeatably under change, the operational documentation is still incomplete.
