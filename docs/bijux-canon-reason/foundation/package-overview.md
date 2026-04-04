---
title: Package Overview
audience: mixed
type: guide
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# Package Overview

`bijux-canon-reason` is the package that owns deterministic evidence-aware reasoning, claim formation, verification, and traceable reasoning workflows.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon-reason"] --> section["Foundation"]
    section --> page["Package Overview"]
    dest1["reviewable boundaries"]
    dest2["operator clarity"]
    dest3["change safety"]
    page --> dest1
    page --> dest2
    page --> dest3
```

## What It Owns

- reasoning plans, claims, and evidence-aware reasoning models
- execution of reasoning steps and local tool dispatch
- verification and provenance checks that belong to reasoning itself
- package-local CLI and API boundaries

## What It Does Not Own

- runtime persistence and replay authority
- ingest and index engines
- repository tooling and release automation

## Purpose

This page gives the shortest honest description of what the package is for.

## Stability

Keep it aligned with the real package boundary described by the code and tests.
