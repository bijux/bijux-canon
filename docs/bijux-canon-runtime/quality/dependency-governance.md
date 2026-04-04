---
title: Dependency Governance
audience: mixed
type: guide
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-04
---

# Dependency Governance

Dependency changes in `bijux-canon-runtime` should be treated as contract changes when they
alter package authority, operational risk, or public setup expectations.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-runtime"] --> section["Quality"]
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
    focus1_1["flow execution authority"]
    focus1 --> focus1_1
    focus1_2["replay and acceptability semantics"]
    focus1 --> focus1_2
    focus2["Evidence to inspect"]
    page --> focus2
    focus2_1["src/bijux_canon_runtime/model"]
    focus2 --> focus2_1
    focus2_2["execution store records"]
    focus2 --> focus2_2
    focus3["Review pressure"]
    page --> focus3
    focus3_1["Quality"]
    focus3 --> focus3_1
    focus3_2["tests/unit for api, contracts, core, interfaces, model, and runtime"]
    focus3 --> focus3_2
```

## Current Dependency Themes

- bijux-canon-agent
- bijux-canon-ingest
- bijux-canon-reason
- bijux-canon-index
- duckdb
- pydantic

## What This Page Answers

- what proves the bijux-canon-runtime contract today
- which risks or limits still need explicit review
- what a reviewer should verify before accepting change

## Purpose

This page explains why dependency review matters for the package.

## Stability

Keep it aligned with `pyproject.toml` and the package's real dependency posture.
