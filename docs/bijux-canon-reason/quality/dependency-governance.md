---
title: Dependency Governance
audience: mixed
type: guide
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# Dependency Governance

Dependency changes in `bijux-canon-reason` should be treated as contract changes when they
alter package authority, operational risk, or public setup expectations.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-reason"] --> section["Quality"]
    section --> page["Dependency Governance"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Dependency Governance"]
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

## Current Dependency Themes

- pydantic
- typer
- fastapi

## What This Page Answers

- what proves the bijux-canon-reason contract today
- which risks or limits still need explicit review
- what a reviewer should verify before accepting change

## Purpose

This page explains why dependency review matters for the package.

## Stability

Keep it aligned with `pyproject.toml` and the package's real dependency posture.
