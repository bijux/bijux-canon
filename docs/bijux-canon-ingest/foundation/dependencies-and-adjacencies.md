---
title: Dependencies and Adjacencies
audience: mixed
type: guide
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-04
---

# Dependencies and Adjacencies

Package dependencies matter because they reveal which behavior is local and which behavior is delegated.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-ingest"] --> section["Foundation"]
    section --> page["Dependencies and Adjacencies"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Direct Dependency Themes

- pydantic
- msgpack
- numpy
- fastapi
- uvicorn
- PyYAML

## Adjacent Package Relationships

- feeds prepared material toward bijux-canon-index and bijux-canon-reason
- stays under runtime governance instead of defining replay authority itself

## Purpose

This page explains which surrounding tools and packages `bijux-canon-ingest` depends on to do its job.

## Stability

Keep it aligned with `pyproject.toml` and the actual package seams.
