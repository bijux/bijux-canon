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

```mermaid
flowchart TD
    page["Public Imports"]
    focus1["Owned package surface"]
    page --> focus1
    focus1_1["flow execution authority"]
    focus1 --> focus1_1
    focus1_2["replay and acceptability semantics"]
    focus1 --> focus1_2
    focus2["Evidence to inspect"]
    page --> focus2
    focus2_1["src/bijux_canon_runtime/model"]
    focus2 --> focus2_1
    focus2_2["execution store records"]
    focus2 --> focus2_2
    focus3["Review pressure"]
    page --> focus3
    focus3_1["Interfaces"]
    focus3 --> focus3_1
    focus3_2["tests/unit for api, contracts, core, interfaces, model, and runtime"]
    focus3 --> focus3_2
```

## Import Anchor

- import root: `bijux_canon_runtime`
- package source root: `packages/bijux-canon-runtime/src/bijux_canon_runtime`

## Use This Page When

- you need the public command, API, import, or artifact surface
- you are checking whether a caller can rely on a given shape or entrypoint
- you need the contract-facing side of the package before using it

## What This Page Answers

- which public or operator-facing surfaces bijux-canon-runtime exposes
- which artifacts and schemas act like contracts
- what compatibility pressure this surface creates

## Reviewer Lens

- compare commands, API files, imports, and artifacts against the documented surface
- check whether schema or artifact changes need compatibility review
- confirm that operator-facing examples still point at real entrypoints

## Honesty Boundary

This page can identify the intended public surfaces of bijux-canon-runtime, but real compatibility still depends on code, schemas, artifacts, and tests staying aligned.

## Purpose

This page keeps the import-facing contract visible when refactoring package internals.

## Stability

Keep it aligned with the actual package source tree and documented import paths.
