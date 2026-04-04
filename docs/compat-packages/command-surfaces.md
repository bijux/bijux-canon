---
title: Command Surfaces
audience: mixed
type: guide
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Command Surfaces

Some compatibility packages also preserve historic command names so migration
does not break operator scripts immediately.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Compatibility Handbook"]
    section --> page["Command Surfaces"]
    dest1["legacy package names"]
    dest2["migration decisions"]
    dest3["retirement review"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Command Rule

A compatibility command should only exist when the canonical package still
provides a meaningful route behind it.

## Purpose

This page records the intent behind legacy command preservation.

## Stability

Keep it aligned with the command declarations in compatibility package metadata.
