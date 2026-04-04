---
title: Artifact Contracts
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Artifact Contracts

Produced artifacts are part of the package contract whenever another package, operator,
or replay workflow depends on them.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-index"] --> section["Interfaces"]
    section --> page["Artifact Contracts"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Artifact Contracts"]
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

## Current Artifacts

- vector execution result collections
- provenance and replay comparison reports
- backend-specific metadata and audit output

## Concrete Anchors

- CLI modules under src/bijux_canon_index/interfaces/cli
- HTTP app under src/bijux_canon_index/api
- OpenAPI schema files under apis/bijux-canon-index/v1
- apis/bijux-canon-index/v1/schema.yaml

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

This page marks which outputs need stable review when behavior changes.

## Stability

Keep it aligned with the package outputs that are actually produced and consumed.

## Core Claim

The interface claim of `bijux-canon-index` is that commands, APIs, imports, schemas, and artifacts form a reviewable contract rather than an implied one.

## Why It Matters

If the interface pages for `bijux-canon-index` are weak, callers cannot tell which commands, schemas, or artifacts are stable enough to depend on, and compatibility review arrives too late.

## If It Drifts

- callers depend on surfaces that are less stable than the docs imply
- schema and artifact changes stop receiving the compatibility review they need
- operator examples begin pointing at stale or misleading entrypaths

## Representative Scenario

An operator or downstream caller wants to depend on a `bijux-canon-index` surface and needs to know which command, API, schema, import, or artifact is stable enough to treat as a contract.

## Source Of Truth Order

- `packages/bijux-canon-index/src/bijux_canon_index` for the implemented boundary
- `apis/bijux-canon-index/v1/schema.yaml` as tracked contract evidence
- `packages/bijux-canon-index/tests` for compatibility and behavior proof
