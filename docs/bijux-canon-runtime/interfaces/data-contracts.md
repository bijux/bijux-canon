---
title: Data Contracts
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-04
---

# Data Contracts

Data contracts in `bijux-canon-runtime` include schemas, structured models, and any stable
payload shape that neighboring systems are expected to understand.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-runtime"] --> section["Interfaces"]
    section --> page["Data Contracts"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Data Contracts"]
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

## Contract Anchors

- apis/bijux-canon-runtime/v1/schema.yaml
- apis/bijux-canon-runtime/v1/schema.hash

## Artifact Anchors

- execution store records
- replay decision artifacts
- non-determinism policy evaluations

## Concrete Anchors

- CLI entrypoint in src/bijux_canon_runtime/interfaces/cli/entrypoint.py
- HTTP app in src/bijux_canon_runtime/api/v1
- schema files in apis/bijux-canon-runtime/v1
- apis/bijux-canon-runtime/v1/schema.yaml

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

This page explains which structured shapes deserve compatibility review.

## Stability

Keep it aligned with tracked schemas, stable models, and durable artifacts.

## Core Claim

The interface claim of `bijux-canon-runtime` is that commands, APIs, imports, schemas, and artifacts form a reviewable contract rather than an implied one.

## Why It Matters

If the interface pages for `bijux-canon-runtime` are weak, callers cannot tell which commands, schemas, or artifacts are stable enough to depend on, and compatibility review arrives too late.

## If It Drifts

- callers depend on surfaces that are less stable than the docs imply
- schema and artifact changes stop receiving the compatibility review they need
- operator examples begin pointing at stale or misleading entrypaths
