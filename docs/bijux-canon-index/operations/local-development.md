---
title: Local Development
audience: mixed
type: guide
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Local Development

Local development should happen inside `packages/bijux-canon-index` with tests and docs updated
in the same change series as the code.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-index"] --> section["Operations"]
    section --> page["Local Development"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Local Development"]
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

## Development Anchors

- tests/unit for API, application, contracts, domain, infra, and tooling
- tests/e2e for CLI workflows, API smoke, determinism gates, and provenance gates
- tests/conformance and tests/compat_v01 for compatibility behavior
- tests/stress and tests/scenarios for operational pressure checks

## What This Page Answers

- how bijux-canon-index is installed, run, diagnosed, and released
- which files or tests matter during package operation
- where an operator should look when behavior changes

## Purpose

This page records the package-local development posture.

## Stability

Keep it aligned with the actual test layout and maintenance workflow.
