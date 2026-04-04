---
title: Documentation Standards
audience: mixed
type: guide
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-04
---

# Documentation Standards

Package docs should stay consistent with the shared handbook layout used across the repository.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-agent"] --> section["Quality"]
    section --> page["Documentation Standards"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Documentation Standards"]
    focus1["Owned package surface"]
    page --> focus1
    focus1_1["agent role implementations and role-specific helpers"]
    focus1 --> focus1_1
    focus1_2["deterministic orchestration of the local agent pipeline"]
    focus1 --> focus1_2
    focus2["Evidence to inspect"]
    page --> focus2
    focus2_1["src/bijux_canon_agent/agents"]
    focus2 --> focus2_1
    focus2_2["trace-backed final outputs"]
    focus2 --> focus2_2
    focus3["Review pressure"]
    page --> focus3
    focus3_1["Quality"]
    focus3 --> focus3_1
    focus3_2["tests/unit for local behavior and utility coverage"]
    focus3 --> focus3_2
```

## Standards

- use the shared five-category package spine
- prefer stable filenames that describe durable intent
- keep docs grounded in real code paths, interfaces, and artifacts

## What This Page Answers

- what proves the bijux-canon-agent contract today
- which risks or limits still need explicit review
- what a reviewer should verify before accepting change

## Purpose

This page keeps package docs from drifting back into ad hoc structure.

## Stability

Update it only when the shared documentation system itself changes.
