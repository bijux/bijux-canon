---
title: Package Behavior
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# Package Behavior

Each compatibility package should stay intentionally thin. Its job is to
preserve a narrow bridge to the canonical package through metadata, imports,
commands, and documentation routing.

## Expected Behavior

- preserve legacy name continuity for installs, imports, or commands
- point clearly at the canonical replacement in package metadata and docs
- avoid growing a separate feature surface or product identity

## Failure Signs

- the compatibility package starts carrying new behavior of its own
- documentation makes the legacy name sound like a preferred starting point
- release activity exists only to mirror canonical releases without a real
  dependent environment behind it

## First Proof Check

- `packages/compat-*`
- compatibility package `README.md` files
- release and retirement rules in the migration handbook
