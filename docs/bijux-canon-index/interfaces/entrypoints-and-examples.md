---
title: Entrypoints and Examples
audience: mixed
type: guide
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Entrypoints and Examples

The fastest way to understand the package interfaces is to pair entrypoints with concrete examples.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-index"] --> section["Interfaces"]
    section --> page["Entrypoints and Examples"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Entrypoints

- CLI modules under src/bijux_canon_index/interfaces/cli
- HTTP app under src/bijux_canon_index/api
- OpenAPI schema files under apis/bijux-canon-index/v1

## Example Anchors

- tests/e2e and tests/scenarios as executable usage guides
- apis/bijux-canon-index/v1/openapi.v1.json for HTTP contract shape

## Purpose

This page records where maintainers can find real invocation examples instead of inventing them from scratch.

## Stability

Keep it aligned with the checked-in examples, fixtures, and executable tests.
