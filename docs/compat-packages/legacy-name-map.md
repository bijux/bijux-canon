---
title: Legacy Name Map
audience: mixed
type: guide
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Legacy Name Map

- `agentic-flows` maps to `bijux-canon-runtime`
- `bijux-agent` maps to `bijux-canon-agent`
- `bijux-rag` maps to `bijux-canon-ingest`
- `bijux-rar` maps to `bijux-canon-reason`
- `bijux-vex` maps to `bijux-canon-index`

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Compatibility Handbook"]
    section --> page["Legacy Name Map"]
    dest1["legacy package names"]
    dest2["migration decisions"]
    dest3["retirement review"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Legacy Name Map"]
    focus1["Legacy surface"]
    page --> focus1
    focus1_1["distribution names"]
    focus1 --> focus1_1
    focus1_2["import names"]
    focus1 --> focus1_2
    focus2["Canonical target"]
    page --> focus2
    focus2_1["current packages"]
    focus2 --> focus2_1
    focus2_2["new work"]
    focus2 --> focus2_2
    focus3["Decision pressure"]
    page --> focus3
    focus3_1["migration"]
    focus3 --> focus3_1
    focus3_2["retirement"]
    focus3 --> focus3_2
```

## What This Page Answers

- which legacy surface is still preserved
- when new work should move to the canonical package instead
- what evidence would justify retiring a compatibility package

## Purpose

This page provides the exact mapping between retired public names and current canonical names.

## Stability

Update it only when a compatibility package is added or retired.
