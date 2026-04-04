---
title: Operator Workflows
audience: mixed
type: guide
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-04
---

# Operator Workflows

Operator workflows should start from documented package entrypoints and end in reviewable outputs.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-runtime"] --> section["Interfaces"]
    section --> page["Operator Workflows"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Operator Workflows"]
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

## Workflow Anchors

- entry surfaces: CLI entrypoint in src/bijux_canon_runtime/interfaces/cli/entrypoint.py, HTTP app in src/bijux_canon_runtime/api/v1, schema files in apis/bijux-canon-runtime/v1
- durable outputs: execution store records, replay decision artifacts, non-determinism policy evaluations
- validation backstops: tests/unit for api, contracts, core, interfaces, model, and runtime, tests/e2e for governed flow behavior

## What This Page Answers

- which public or operator-facing surfaces bijux-canon-runtime exposes
- which artifacts and schemas act like contracts
- what compatibility pressure this surface creates

## Purpose

This page connects package interfaces to the workflows an operator actually performs.

## Stability

Keep it aligned with the existing commands, endpoints, and outputs.
