---
title: Local Development
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Local Development

Local development for `bijux-canon-ingest` should keep code, docs, and proof close enough together that changes to prepared ingest behavior stay easy to explain before they spread outward.

## What To Check

- work from the package boundary rather than from incidental monorepo context
- change docs and tests in the same series when local behavior changes
- treat a hard-to-reproduce edit loop as an operational defect, not a personal preference

## First Proof Check

- `pyproject.toml`, `README.md`, and boundary-facing entrypoints for checked-in operating truth
- `tests` and runnable workflows for executable confirmation that the runbook still works
- release notes and version metadata when the work changes caller expectations

## Bottom Line

If `bijux-canon-ingest` cannot be operated repeatably under change, the operational documentation is still incomplete.
