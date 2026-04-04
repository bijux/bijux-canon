---
title: Known Limitations
audience: mixed
type: guide
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Known Limitations

No package is improved by pretending its limitations do not exist.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-index"] --> section["Quality"]
    section --> page["Known Limitations"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Honest Boundaries

- document ingestion and normalization
- runtime-wide replay policy and execution governance
- repository maintenance automation

## Purpose

This page keeps limitation language attached to the package boundary instead of scattered through issue comments.

## Stability

Keep it aligned with the limitations that remain intentionally true today.
