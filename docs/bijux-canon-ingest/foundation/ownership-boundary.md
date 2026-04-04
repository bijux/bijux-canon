---
title: Ownership Boundary
audience: mixed
type: guide
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-04
---

# Ownership Boundary

Ownership in `bijux-canon-ingest` is easiest to read from the source tree plus the tests that protect it.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-ingest"] --> section["Foundation"]
    section --> page["Ownership Boundary"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Ownership Boundary"]
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
    focus3_1["Foundation"]
    focus3 --> focus3_1
    focus3_2["tests/unit for module-level behavior across processing, retrieval, and interfaces"]
    focus3 --> focus3_2
```

## Owned Code Areas

- `src/bijux_canon_ingest/processing` for deterministic document transforms
- `src/bijux_canon_ingest/retrieval` for retrieval-oriented models and assembly
- `src/bijux_canon_ingest/application` for package workflows
- `src/bijux_canon_ingest/infra` for local adapters and infrastructure helpers
- `src/bijux_canon_ingest/interfaces` for CLI and HTTP boundaries
- `src/bijux_canon_ingest/safeguards` for protective rules for ingest behavior

## Adjacent Systems

- feeds prepared material toward bijux-canon-index and bijux-canon-reason
- stays under runtime governance instead of defining replay authority itself

## What This Page Answers

- what bijux-canon-ingest is expected to own
- what remains outside the package boundary
- which neighboring seams a reviewer should compare next

## Purpose

This page ties package ownership to concrete directories instead of abstract slogans.

## Stability

Keep it aligned with the current module layout.
