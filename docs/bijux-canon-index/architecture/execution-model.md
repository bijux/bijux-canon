---
title: Execution Model
audience: mixed
type: guide
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Execution Model

`bijux-canon-index` executes work by receiving inputs at its interfaces, coordinating policy
and workflows in application code, and delegating specific responsibilities to owned modules.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-index"] --> section["Architecture"]
    section --> page["Execution Model"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Execution Anchors

- entry surfaces: CLI modules under src/bijux_canon_index/interfaces/cli, HTTP app under src/bijux_canon_index/api, OpenAPI schema files under apis/bijux-canon-index/v1
- workflow modules: src/bijux_canon_index/domain, src/bijux_canon_index/application, src/bijux_canon_index/infra
- outputs: vector execution result collections, provenance and replay comparison reports, backend-specific metadata and audit output

## Purpose

This page summarizes the package execution model before readers inspect individual modules.

## Stability

Keep it aligned with the actual workflow code and entrypoints.
