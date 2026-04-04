---
title: Failure Recovery
audience: mixed
type: guide
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Failure Recovery

Failure recovery starts with knowing which artifacts, interfaces, and tests expose the problem.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-index"] --> section["Operations"]
    section --> page["Failure Recovery"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Failure Recovery"]
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
    focus3_1["Operations"]
    focus3 --> focus3_1
    focus3_2["tests/unit for API, application, contracts, domain, infra, and tooling"]
    focus3 --> focus3_2
```

## Recovery Anchors

- interface surfaces: CLI modules under src/bijux_canon_index/interfaces/cli, HTTP app under src/bijux_canon_index/api, OpenAPI schema files under apis/bijux-canon-index/v1
- artifacts to inspect: vector execution result collections, provenance and replay comparison reports, backend-specific metadata and audit output
- tests to run: tests/unit for API, application, contracts, domain, infra, and tooling, tests/e2e for CLI workflows, API smoke, determinism gates, and provenance gates

## What This Page Answers

- how bijux-canon-index is installed, run, diagnosed, and released
- which files or tests matter during package operation
- where an operator should look when behavior changes

## Purpose

This page gives maintainers a durable frame for triaging package failures.

## Stability

Keep it aligned with the package entrypoints and diagnostic outputs.
