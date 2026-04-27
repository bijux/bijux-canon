---
title: Release and Versioning
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Release and Versioning

Release and versioning for `bijux-canon-ingest` should explain how changes to prepared ingest behavior become visible to readers and callers. Version numbers are only credible when the release story names what changed and why.

## What To Check

- tie release notes, version metadata, and surface changes together
- treat undocumented breakage as a release failure even when packaging succeeds
- separate package-local release facts from wider repository conventions

## First Proof Check

- `pyproject.toml`, `README.md`, and boundary-facing entrypoints for checked-in operating truth
- `tests` and runnable workflows for executable confirmation that the runbook still works
- release notes and version metadata when the work changes caller expectations

## Bottom Line

If `bijux-canon-ingest` cannot be operated repeatably under change, the operational documentation is still incomplete.
