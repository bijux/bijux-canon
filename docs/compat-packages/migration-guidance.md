---
title: Migration Guidance
audience: mixed
type: guide
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Migration Guidance

New work should target the canonical package names directly and treat the
compatibility packages as temporary bridges.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Compatibility Handbook"]
    section --> page["Migration Guidance"]
    dest1["legacy package names"]
    dest2["migration decisions"]
    dest3["retirement review"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Recommended Migration Pattern

- switch dependencies to the canonical `bijux-canon-*` distribution
- switch imports to the canonical package docs and source roots
- keep compatibility packages only where an external environment still depends on them

## Purpose

This page tells maintainers how to move away from legacy names without ambiguity.

## Stability

Keep it aligned with the canonical packages that compatibility packages currently point to.
