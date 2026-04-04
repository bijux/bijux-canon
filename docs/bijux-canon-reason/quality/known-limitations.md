---
title: Known Limitations
audience: mixed
type: guide
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# Known Limitations

No package is improved by pretending its limitations do not exist.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-reason"] --> section["Quality"]
    section --> page["Known Limitations"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Known Limitations"]
    focus1["Owned package surface"]
    page --> focus1
    focus1_1["reasoning plans, claims, and evidence-aware reasoning models"]
    focus1 --> focus1_1
    focus1_2["execution of reasoning steps and local tool dispatch"]
    focus1 --> focus1_2
    focus2["Evidence to inspect"]
    page --> focus2
    focus2_1["src/bijux_canon_reason/planning"]
    focus2 --> focus2_1
    focus2_2["reasoning traces and replay diffs"]
    focus2 --> focus2_2
    focus3["Review pressure"]
    page --> focus3
    focus3_1["Quality"]
    focus3 --> focus3_1
    focus3_2["tests/unit for planning, reasoning, execution, verification, and interfaces"]
    focus3 --> focus3_2
```

## Honest Boundaries

- runtime persistence and replay authority
- ingest and index engines
- repository tooling and release automation

## What This Page Answers

- what proves the bijux-canon-reason contract today
- which risks or limits still need explicit review
- what a reviewer should verify before accepting change

## Purpose

This page keeps limitation language attached to the package boundary instead of scattered through issue comments.

## Stability

Keep it aligned with the limitations that remain intentionally true today.
