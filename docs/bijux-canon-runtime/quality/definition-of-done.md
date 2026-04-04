---
title: Definition of Done
audience: mixed
type: guide
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-04
---

# Definition of Done

A change in `bijux-canon-runtime` is not done when code passes locally but the package contract
is still unclear or unprotected.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-runtime"] --> section["Quality"]
    section --> page["Definition of Done"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Done Means

- code, docs, and tests agree on the new behavior
- public surfaces and artifacts remain explainable
- release-facing impact is visible when compatibility changes

## Purpose

This page records the package's completion threshold.

## Stability

Keep it aligned with the package validation and release expectations.
