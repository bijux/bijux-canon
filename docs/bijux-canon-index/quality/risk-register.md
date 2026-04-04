---
title: Risk Register
audience: mixed
type: guide
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Risk Register

The durable risks for `bijux-canon-index` are the ones that make the package boundary, interface contract,
or produced artifacts harder to trust.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-index"] --> section["Quality"]
    section --> page["Risk Register"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Ongoing Risks to Watch

- hidden overlap with neighboring packages
- drift between docs, code, and tests
- compatibility changes that are not made explicit

## Purpose

This page keeps long-lived package risks visible to maintainers.

## Stability

Update it when the durable risk profile changes, not for routine day-to-day churn.
