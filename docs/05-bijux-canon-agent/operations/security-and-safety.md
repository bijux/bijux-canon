---
title: Security and Safety
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Security and Safety

Security and safety review for `bijux-canon-agent` should start from the real authority the package holds over workflow and trace behavior. Generic caution language is weaker than a clear statement of what the package can actually affect.

## What To Check

- name the boundary surfaces that add real authority or risk
- treat any expansion of authority as a docs, tests, and release concern at the same time
- separate package-local safety concerns from repository-wide governance owned elsewhere

## First Proof Check

- `pyproject.toml`, `README.md`, and boundary-facing entrypoints for checked-in operating truth
- `tests` and runnable workflows for executable confirmation that the runbook still works
- release notes and version metadata when the work changes caller expectations

## Bottom Line

If `bijux-canon-agent` cannot be operated repeatably under change, the operational documentation is still incomplete.
