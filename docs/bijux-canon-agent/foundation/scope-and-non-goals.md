---
title: Scope and Non-Goals
audience: mixed
type: guide
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-04
---

# Scope and Non-Goals

The package boundary exists so neighboring packages can evolve without hidden overlap.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-agent"] --> section["Foundation"]
    section --> page["Scope and Non-Goals"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Scope and Non-Goals"]
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
    focus3_1["Foundation"]
    focus3 --> focus3_1
    focus3_2["tests/unit for local behavior and utility coverage"]
    focus3 --> focus3_2
```

## In Scope

- agent role implementations and role-specific helpers
- deterministic orchestration of the local agent pipeline
- trace-backed result artifacts that explain each run
- package-local CLI and HTTP boundaries for agent workflows

## Out of Scope

- runtime-wide persistence and replay acceptance
- ingest and index domain ownership
- repository tooling and release automation

## What This Page Answers

- what bijux-canon-agent is expected to own
- what remains outside the package boundary
- which neighboring seams a reviewer should compare next

## Purpose

This page keeps future work from leaking into the wrong package.

## Stability

Update it only when ownership truly moves into or out of `bijux-canon-agent`.
