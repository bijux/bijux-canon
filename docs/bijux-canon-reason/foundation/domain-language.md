---
title: Domain Language
audience: mixed
type: guide
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# Domain Language

The package should use language that reflects its actual ownership instead of borrowing
vague names from neighboring packages.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-reason"] --> section["Foundation"]
    section --> page["Domain Language"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Package Vocabulary Anchors

- package name: `bijux-canon-reason`
- Python import root: `bijux_canon_reason`
- owning package directory: `packages/bijux-canon-reason`
- key outputs: reasoning traces and replay diffs, claim and verification outcomes, evaluation suite artifacts

## Purpose

This page records the naming anchors that should stay stable in docs, code, and review discussions.

## Stability

Keep it aligned with the package's real import names, directories, and artifact nouns.
