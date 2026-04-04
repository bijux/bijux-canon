---
title: Observability and Diagnostics
audience: mixed
type: guide
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Observability and Diagnostics

Diagnostics should make it easier to explain what `bijux-canon-index` did, not merely that it ran.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-index"] --> section["Operations"]
    section --> page["Observability and Diagnostics"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## Diagnostic Anchors

- vector execution result collections
- provenance and replay comparison reports
- backend-specific metadata and audit output

## Supporting Modules

- `src/bijux_canon_index/domain` for execution, provenance, and request semantics
- `src/bijux_canon_index/application` for workflow coordination

## Purpose

This page points readers toward the package's observable output and diagnostic support.

## Stability

Keep it aligned with the package modules and artifacts that currently support diagnosis.
