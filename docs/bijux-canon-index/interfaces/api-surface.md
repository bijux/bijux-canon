---
title: API Surface
audience: mixed
type: guide
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# API Surface

HTTP-facing behavior should be discoverable from tracked schema files and the owning API modules.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-index"] --> section["Interfaces"]
    section --> page["API Surface"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["API Surface"]
    focus1["Owned package surface"]
    page --> focus1
    focus1_1["vector execution semantics and backend orchestration"]
    focus1 --> focus1_1
    focus1_2["provenance-aware result artifacts and replay-oriented comparison"]
    focus1 --> focus1_2
    focus2["Evidence to inspect"]
    page --> focus2
    focus2_1["src/bijux_canon_index/domain"]
    focus2 --> focus2_1
    focus2_2["vector execution result collections"]
    focus2 --> focus2_2
    focus3["Review pressure"]
    page --> focus3
    focus3_1["Interfaces"]
    focus3 --> focus3_1
    focus3_2["tests/unit for API, application, contracts, domain, infra, and tooling"]
    focus3 --> focus3_2
```

## API Artifacts

- apis/bijux-canon-index/v1/schema.yaml
- apis/bijux-canon-index/v1/openapi.v1.json

## Boundary Modules

- CLI modules under src/bijux_canon_index/interfaces/cli
- HTTP app under src/bijux_canon_index/api
- OpenAPI schema files under apis/bijux-canon-index/v1

## Use This Page When

- you need the public command, API, import, or artifact surface
- you are checking whether a caller can rely on a given shape or entrypoint
- you need the contract-facing side of the package before using it

## What This Page Answers

- which public or operator-facing surfaces bijux-canon-index exposes
- which artifacts and schemas act like contracts
- what compatibility pressure this surface creates

## Reviewer Lens

- compare commands, API files, imports, and artifacts against the documented surface
- check whether schema or artifact changes need compatibility review
- confirm that operator-facing examples still point at real entrypoints

## Honesty Boundary

This page can identify the intended public surfaces of bijux-canon-index, but real compatibility still depends on code, schemas, artifacts, and tests staying aligned.

## Purpose

This page ties API behavior to tracked code and schema assets.

## Stability

Keep it aligned with the actual API modules and schema files.
