---
title: Import Surfaces
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# Import Surfaces

Compatibility imports exist so older code can keep resolving package names while
migration is underway. They are continuity aids, not first-class imports for
new code.

## Current Import Map

- `agentic_flows` -> `bijux_canon_runtime`
- `bijux_agent` -> `bijux_canon_agent`
- `bijux_rag` -> `bijux_canon_ingest`
- `bijux_rar` -> `bijux_canon_reason`
- `bijux_vex` -> `bijux_canon_index`

## Review Rule

A preserved import is justified only while supported code still depends on it.
New code should use canonical imports even if the compatibility import still
resolves.

## First Proof Check

- `packages/compat-*`
- compatibility package `README.md` routing
- repository-wide search for remaining legacy imports
