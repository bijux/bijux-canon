---
title: Review Checklist
audience: mixed
type: guide
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# Review Checklist

Reviewing changes in `bijux-canon-reason` should include both behavior and documentation.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-reason"] --> section["Quality"]
    section --> page["Review Checklist"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Checklist

- did ownership stay inside the correct package boundary
- do interface or artifact changes have matching docs and tests
- are filenames, commit messages, and symbols still clear enough to age well

## Purpose

This page records a compact review lens for package changes.

## Stability

Update it only when the package review posture genuinely changes.
