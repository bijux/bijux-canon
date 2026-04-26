---
title: Legacy Name Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# Legacy Name Map

The legacy-name map is the shortest route from an old public name to its
canonical replacement. It exists to remove ambiguity, not to make the old names
feel equally current.

## Current Map

- `agentic-flows` -> `bijux-canon-runtime`
- `bijux-agent` -> `bijux-canon-agent`
- `bijux-rag` -> `bijux-canon-ingest`
- `bijux-rar` -> `bijux-canon-reason`
- `bijux-vex` -> `bijux-canon-index`

## What To Check Next

- the compatibility package `README.md` for the checked-in canonical target
- the canonical package handbook for current behavior
- migration pages when the question turns from mapping into retirement timing

## First Proof Check

- `packages/compat-*`
- compatibility package `README.md` files
- canonical handbooks under `docs/02-bijux-canon-ingest/` through
  `docs/06-bijux-canon-runtime/`
