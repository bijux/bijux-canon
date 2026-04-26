---
title: Package Dispatch
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-09
---

# Package Dispatch

Package dispatch is how shared make workflows become package-specific without
duplicating the whole command model.

The repository uses `makes/bijux-py/root/package-dispatch.mk`,
`makes/packages/compat-package.mk`, and the per-package files under
`makes/packages/` to route shared target families onto real package roots and
artifact directories.

## Dispatch Anchors

- `makes/packages/bijux-canon-*.mk` for canonical package bindings
- `makes/packages/compat-package.mk` for compatibility-package routing
- `makes/bijux-py/package-catalog.mk` and related package fragments for shared
  package metadata

