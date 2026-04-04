---
title: CLI Surface
audience: mixed
type: guide
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-04
---

# CLI Surface

The CLI surface is the operator-facing command layer for `bijux-canon-ingest`.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-ingest"] --> section["Interfaces"]
    section --> page["CLI Surface"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Command Facts

- canonical command: `bijux-canon-ingest`
- interface modules: CLI entrypoint in src/bijux_canon_ingest/interfaces/cli/entrypoint.py, HTTP boundaries under src/bijux_canon_ingest/interfaces, configuration modules under src/bijux_canon_ingest/config

## Purpose

This page points maintainers toward the command entrypoints and their owning code.

## Stability

Keep it aligned with the declared scripts and the interface modules that implement them.
