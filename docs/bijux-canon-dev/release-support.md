---
title: Release Support
audience: mixed
type: guide
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# Release Support

Shared release helpers belong here so versioning and packaging practices stay
consistent across the repository.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Maintainer Handbook"]
    section --> page["Release Support"]
    dest1["quality gates"]
    dest2["schema governance"]
    dest3["release support"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Current Surfaces

- `release/version_resolver.py`
- package metadata checks in tests
- root commit conventions configured through commitizen

## Purpose

This page records the maintenance package role in release preparation.

## Stability

Keep it aligned with the real release support code and the actual versioning workflow.
