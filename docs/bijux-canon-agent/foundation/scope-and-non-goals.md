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

## In Scope

- agent role implementations and role-specific helpers
- deterministic orchestration of the local agent pipeline
- trace-backed result artifacts that explain each run
- package-local CLI and HTTP boundaries for agent workflows

## Out of Scope

- runtime-wide persistence and replay acceptance
- ingest and index domain ownership
- repository tooling and release automation

## Purpose

This page keeps future work from leaking into the wrong package.

## Stability

Update it only when ownership truly moves into or out of `bijux-canon-agent`.
