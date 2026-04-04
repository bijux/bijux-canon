---
title: Public Imports
audience: mixed
type: guide
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-04
---

# Public Imports

The public Python surface of `bijux-canon-runtime` starts at the package import root and any
intentionally exported modules beneath it.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-runtime"] --> section["Interfaces"]
    section --> page["Public Imports"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Import Anchor

- import root: `bijux_canon_runtime`
- package source root: `packages/bijux-canon-runtime/src/bijux_canon_runtime`

## Purpose

This page keeps the import-facing contract visible when refactoring package internals.

## Stability

Keep it aligned with the actual package source tree and documented import paths.
