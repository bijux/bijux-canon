---
title: Repository Consolidation
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Repository Consolidation

The compatibility packages exist because the public package family has been
consolidated into the single `bijux-canon` repository.

That means the standalone repositories that originally carried the public names
below should be treated as retired entrypoints:

- `https://github.com/bijux/agentic-flows` now maps to `bijux-canon-runtime`
- `https://github.com/bijux/bijux-agent` now maps to `bijux-canon-agent`
- `https://github.com/bijux/bijux-rag` now maps to `bijux-canon-ingest`
- `https://github.com/bijux/bijux-rar` now maps to `bijux-canon-reason`
- `https://github.com/bijux/bijux-vex` now maps to `bijux-canon-index`

The consolidated source of truth for all of them is now:

- repository: `https://github.com/bijux/bijux-canon`
- repository handbook: `https://bijux.io/bijux-canon/`
- shared migration guide: `https://bijux.io/bijux-canon/compat-packages/migration-guidance/`

## What Should Change

- dependency declarations should move to the canonical `bijux-canon-*` package
- import paths should move to the canonical Python package names
- links in docs, issue templates, and onboarding material should point to
  `bijux-canon` rather than the retired standalone repositories

## Legacy Name Map

- `agentic-flows` -> `bijux-canon-runtime`
- `bijux-agent` -> `bijux-canon-agent`
- `bijux-rag` -> `bijux-canon-ingest`
- `bijux-rar` -> `bijux-canon-reason`
- `bijux-vex` -> `bijux-canon-index`

## Why This Page Exists

Readers landing on a legacy package page should be able to answer three
questions immediately:

- which canonical package now owns the work
- which repository now owns the source of truth
- where the migration path is documented

If any of those answers are ambiguous, the consolidation is still incomplete.
