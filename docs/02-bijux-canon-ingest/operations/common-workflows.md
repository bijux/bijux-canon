---
title: Common Workflows
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Common Workflows

Common workflows should show the recurring paths maintainers actually follow when changing or re-running `bijux-canon-ingest`. If a recurring path is still reconstructed from memory, the runbook is incomplete.

## What To Check

- name the repeatable path from entrypoint to owned code to proof
- separate the common path from special-case debugging or one-off repair work
- treat repeated oral instructions as a sign that the workflow still is not documented tightly enough

## First Proof Check

- `pyproject.toml`, `README.md`, and boundary-facing entrypoints for checked-in operating truth
- `tests` and runnable workflows for executable confirmation that the runbook still works
- release notes and version metadata when the work changes caller expectations

## Bottom Line

If `bijux-canon-ingest` cannot be operated repeatably under change, the operational documentation is still incomplete.
