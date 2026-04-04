---
title: Public Imports
audience: mixed
type: guide
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-04
---

# Public Imports

The public Python surface of `bijux-canon-agent` starts at the package import root and any
intentionally exported modules beneath it.

## Import Anchor

- import root: `bijux_canon_agent`
- package source root: `packages/bijux-canon-agent/src/bijux_canon_agent`

## Purpose

This page keeps the import-facing contract visible when refactoring package internals.

## Stability

Keep it aligned with the actual package source tree and documented import paths.
