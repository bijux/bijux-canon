---
title: Architecture
audience: mixed
type: index
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-04
---

# Architecture

bijux-canon-ingest architecture pages describe how modules and responsibilities fit together under `bijux_canon_ingest`.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-ingest"] --> section["Architecture"]
    section --> page["Architecture"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Architecture"]
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
    focus3_1["Architecture"]
    focus3 --> focus3_1
    focus3_2["tests/unit for module-level behavior across processing, retrieval, and interfaces"]
    focus3 --> focus3_2
```

## Pages in This Section

- [Module Map](module-map.md)
- [Dependency Direction](dependency-direction.md)
- [Execution Model](execution-model.md)
- [State and Persistence](state-and-persistence.md)
- [Integration Seams](integration-seams.md)
- [Error Model](error-model.md)
- [Extensibility Model](extensibility-model.md)
- [Code Navigation](code-navigation.md)
- [Architecture Risks](architecture-risks.md)

## Read Across the Package

- [Foundation](../foundation/index.md)
- [Interfaces](../interfaces/index.md)
- [Operations](../operations/index.md)
- [Quality](../quality/index.md)

## What This Page Answers

- how bijux-canon-ingest is structured internally
- which modules control the main execution path
- where architectural drift would become visible first

## Purpose

This page explains how to use the architecture section for `bijux-canon-ingest` without repeating the detail that belongs on the topic pages beneath it.

## Stability

This page is part of the canonical package docs spine. Keep it aligned with the current package boundary and the topic pages in this section.
