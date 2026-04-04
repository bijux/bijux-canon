---
title: Configuration Surface
audience: mixed
type: guide
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-04
---

# Configuration Surface

Configuration belongs at the package boundary, not scattered through unrelated modules.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-ingest"] --> section["Interfaces"]
    section --> page["Configuration Surface"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Configuration Surface"]
    focus1["Owned package surface"]
    page --> focus1
    focus1_1["document cleaning, normalization, and chunking"]
    focus1 --> focus1_1
    focus1_2["ingest-local retrieval and indexing assembly"]
    focus1 --> focus1_2
    focus2["Evidence to inspect"]
    page --> focus2
    focus2_1["src/bijux_canon_ingest/processing"]
    focus2 --> focus2_1
    focus2_2["normalized document trees"]
    focus2 --> focus2_2
    focus3["Review pressure"]
    page --> focus3
    focus3_1["Interfaces"]
    focus3 --> focus3_1
    focus3_2["tests/unit for module-level behavior across processing, retrieval, and interfaces"]
    focus3 --> focus3_2
```

## Configuration Anchors

- CLI entrypoint in src/bijux_canon_ingest/interfaces/cli/entrypoint.py
- HTTP boundaries under src/bijux_canon_ingest/interfaces
- configuration modules under src/bijux_canon_ingest/config

## Review Rule

Configuration changes should update the operator docs, schema docs, and tests that protect the same behavior.

## What This Page Answers

- which public or operator-facing surfaces bijux-canon-ingest exposes
- which artifacts and schemas act like contracts
- what compatibility pressure this surface creates

## Purpose

This page explains where configuration enters the package and how it should be reviewed.

## Stability

Keep it aligned with real configuration loaders, defaults, and operator-facing options.
