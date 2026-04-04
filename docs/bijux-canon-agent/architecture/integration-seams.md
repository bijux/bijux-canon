---
title: Integration Seams
audience: mixed
type: guide
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-04
---

# Integration Seams

Integration seams are the points where `bijux-canon-agent` meets configuration, APIs,
operators, or neighboring packages.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-agent"] --> section["Architecture"]
    section --> page["Integration Seams"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Integration Surfaces

- CLI entrypoint in src/bijux_canon_agent/interfaces/cli/entrypoint.py
- operator configuration under src/bijux_canon_agent/config
- HTTP-adjacent modules under src/bijux_canon_agent/api

## Adjacent Systems

- coordinates work that may call ingest, reason, and runtime components
- leans on runtime for governed execution and replay acceptance

## Purpose

This page explains where to look when integration behavior changes.

## Stability

Keep it aligned with real boundary modules and schema files.
