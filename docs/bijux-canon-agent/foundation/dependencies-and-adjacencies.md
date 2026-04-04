---
title: Dependencies and Adjacencies
audience: mixed
type: guide
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-04
---

# Dependencies and Adjacencies

Package dependencies matter because they reveal which behavior is local and which behavior is delegated.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-agent"] --> section["Foundation"]
    section --> page["Dependencies and Adjacencies"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Direct Dependency Themes

- aiohttp
- typer
- click
- pydantic
- fastapi
- openai
- structlog
- pluggy

## Adjacent Package Relationships

- coordinates work that may call ingest, reason, and runtime components
- leans on runtime for governed execution and replay acceptance

## Purpose

This page explains which surrounding tools and packages `bijux-canon-agent` depends on to do its job.

## Stability

Keep it aligned with `pyproject.toml` and the actual package seams.
