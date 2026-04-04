---
title: SBOM and Supply Chain
audience: mixed
type: guide
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# SBOM and Supply Chain

Supply-chain visibility is a repository maintenance concern, so SBOM helpers
live in `bijux-canon-dev` instead of being duplicated by each package.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Maintainer Handbook"]
    section --> page["SBOM and Supply Chain"]
    dest1["quality gates"]
    dest2["schema governance"]
    dest3["release support"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Current Surfaces

- `sbom/requirements_writer.py`
- `tests/test_sbom_requirements_writer.py`
- shared dependency metadata in package `pyproject.toml` files

## Purpose

This page explains the home for supply-chain oriented repository tooling.

## Stability

Keep it aligned with the checked-in SBOM helpers and tests.
