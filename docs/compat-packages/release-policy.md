---
title: Release Policy
audience: mixed
type: guide
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Release Policy

Compatibility packages should release only when they still serve a real
migration need or when the canonical target package changes in a way that
requires compatibility metadata to move with it.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Compatibility Handbook"]
    section --> page["Release Policy"]
    dest1["legacy package names"]
    dest2["migration decisions"]
    dest3["retirement review"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Policy

- keep releases narrow and clearly justified
- avoid feature growth inside the compatibility packages
- document canonical targets in every compatibility package README

## Purpose

This page keeps compatibility releases from drifting into independent product work.

## Stability

Keep it aligned with the current maintenance strategy for legacy packages.
