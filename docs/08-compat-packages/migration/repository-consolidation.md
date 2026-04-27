---
title: Repository Consolidation
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# Repository Consolidation

The compatibility packages exist because the public package family was
consolidated into the single `bijux-canon` repository. The old standalone
repositories are no longer the source of truth for current behavior.

## Retired Repository Map

- `https://github.com/bijux/agentic-flows` -> `bijux-canon-runtime`
- `https://github.com/bijux/bijux-agent` -> `bijux-canon-agent`
- `https://github.com/bijux/bijux-rag` -> `bijux-canon-ingest`
- `https://github.com/bijux/bijux-rar` -> `bijux-canon-reason`
- `https://github.com/bijux/bijux-vex` -> `bijux-canon-index`

## Current Source Of Truth

- repository: `https://github.com/bijux/bijux-canon`
- compatibility handbook: `https://bijux.io/bijux-canon/08-compat-packages/`
- canonical package handbooks under `docs/02-...` through `docs/06-...`

## What Should Change

- dependency declarations should use canonical `bijux-canon-*` package names
- imports and commands should move to canonical names
- docs and links should point to `bijux-canon` rather than retired standalone
  repositories unless the retirement history itself is the topic
