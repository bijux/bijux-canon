---
title: Review Checklist
audience: mixed
type: guide
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-04
---

# Review Checklist

Reviewing changes in `bijux-canon-ingest` should include both behavior and documentation.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-ingest"] --> section["Quality"]
    section --> page["Review Checklist"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Review Checklist"]
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
    focus3_1["Quality"]
    focus3 --> focus3_1
    focus3_2["tests/unit for module-level behavior across processing, retrieval, and interfaces"]
    focus3 --> focus3_2
```

## Checklist

- did ownership stay inside the correct package boundary
- do interface or artifact changes have matching docs and tests
- are filenames, commit messages, and symbols still clear enough to age well

## What This Page Answers

- what proves the bijux-canon-ingest contract today
- which risks or limits still need explicit review
- what a reviewer should verify before accepting change

## Purpose

This page records a compact review lens for package changes.

## Stability

Update it only when the package review posture genuinely changes.
