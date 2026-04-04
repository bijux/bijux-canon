---
title: Data Contracts
audience: mixed
type: guide
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-04
---

# Data Contracts

Data contracts in `bijux-canon-ingest` include schemas, structured models, and any stable
payload shape that neighboring systems are expected to understand.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-ingest"] --> section["Interfaces"]
    section --> page["Data Contracts"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Contract Anchors

- apis/bijux-canon-ingest/v1/schema.yaml

## Artifact Anchors

- normalized document trees
- chunk collections and retrieval-ready records
- diagnostic output produced during ingest workflows

## Purpose

This page explains which structured shapes deserve compatibility review.

## Stability

Keep it aligned with tracked schemas, stable models, and durable artifacts.
