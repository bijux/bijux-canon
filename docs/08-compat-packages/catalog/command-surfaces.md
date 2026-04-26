---
title: Command Surfaces
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# Command Surfaces

Some compatibility packages preserve legacy CLI names so migration does not
break operator scripts immediately. A preserved command is a safety rail on the
way to the canonical package, not a reason to keep new automation on the old
name.

## Current Command Map

- `agentic-flows` -> `bijux-canon-runtime`
- `bijux-agent` -> `bijux-canon-agent`
- `bijux-rag` -> `bijux-canon-ingest`
- `bijux-rar` -> `bijux-canon-reason`
- `bijux-vex` -> `bijux-canon-index`

## Review Rule

Keep a compatibility command only when a real supported environment still calls
it. Once scripts and runbooks move to the canonical command, the compatibility
name is retirement debt.

## First Proof Check

- `packages/compat-*`
- compatibility package metadata and README files
- repository-wide search for remaining legacy CLI usage
