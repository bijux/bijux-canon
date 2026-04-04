---
title: Package Overview
audience: mixed
type: guide
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-04
---

# Package Overview

`bijux-canon-ingest` is the package that owns deterministic document ingestion, chunking, retrieval assembly, and ingest-facing boundaries.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-ingest"] --> section["Foundation"]
    section --> page["Package Overview"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## What It Owns

- document cleaning, normalization, and chunking
- ingest-local retrieval and indexing assembly
- package-local CLI and HTTP boundaries
- ingest-specific safeguards, adapters, and observability helpers

## What It Does Not Own

- runtime-wide replay authority and persistence
- cross-package vector execution semantics
- repository maintenance automation

## Purpose

This page gives the shortest honest description of what the package is for.

## Stability

Keep it aligned with the real package boundary described by the code and tests.
