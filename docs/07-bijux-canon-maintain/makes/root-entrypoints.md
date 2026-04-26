---
title: Root Entrypoints
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-09
---

# Root Entrypoints

Root make entrypoints should be obvious enough that maintainers do not have to
memorize hidden aliases.

The main command surface starts with `Makefile`, `makes/root.mk`,
`makes/env.mk`, and `makes/packages.mk`. Those files establish the repository’s
top-level environment, package enumeration, and shared target routing.

## Anchors

- `Makefile` includes `makes/root.mk`
- `makes/root.mk` is the repository assembly point
- `makes/env.mk` and `makes/packages.mk` provide shared variables and package
  metadata

## Review Rule

If a top-level target cannot be traced quickly from these entrypoints, the make
surface is becoming harder to maintain than it should be.

