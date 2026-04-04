---
title: Retirement Conditions
audience: mixed
type: guide
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Retirement Conditions

A compatibility package can be retired only when the dependent environments
that still need it are understood and the retirement path is documented.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Compatibility Handbook"]
    section --> page["Retirement Conditions"]
    dest1["legacy package names"]
    dest2["migration decisions"]
    dest3["retirement review"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Retirement Signals

- no remaining supported consumers depend on the legacy name
- migration guidance has been in place long enough to be credible
- removal will not silently strand existing automation

## Purpose

This page explains the threshold for removing a compatibility package.

## Stability

Update this page only when the retirement policy itself changes.
