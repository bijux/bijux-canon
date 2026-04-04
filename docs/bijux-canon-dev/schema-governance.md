---
title: Schema Governance
audience: mixed
type: guide
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# Schema Governance

The package owns repository-level helpers that keep API schemas and tracked
schema artifacts synchronized with the code that claims to implement them.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Maintainer Handbook"]
    section --> page["Schema Governance"]
    dest1["quality gates"]
    dest2["schema governance"]
    dest3["release support"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Current Surfaces

- `api/openapi_drift.py`
- tests such as `tests/test_openapi_drift.py`
- root `apis/` directories that store reviewed schema artifacts

## Purpose

This page explains why schema drift detection belongs in the maintainer package.

## Stability

Keep it aligned with the actual drift tooling and tracked schema files.
