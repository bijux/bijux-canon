---
title: API Surface
audience: mixed
type: guide
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-04
---

# API Surface

HTTP-facing behavior should be discoverable from tracked schema files and the owning API modules.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-ingest"] --> section["Interfaces"]
    section --> page["API Surface"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["API Surface"]
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

## API Artifacts

- apis/bijux-canon-ingest/v1/schema.yaml

## Boundary Modules

- CLI entrypoint in src/bijux_canon_ingest/interfaces/cli/entrypoint.py
- HTTP boundaries under src/bijux_canon_ingest/interfaces
- configuration modules under src/bijux_canon_ingest/config

## What This Page Answers

- which public or operator-facing surfaces bijux-canon-ingest exposes
- which artifacts and schemas act like contracts
- what compatibility pressure this surface creates

## Purpose

This page ties API behavior to tracked code and schema assets.

## Stability

Keep it aligned with the actual API modules and schema files.
