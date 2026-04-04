---
title: Quality Gates
audience: mixed
type: guide
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# Quality Gates

Repository quality checks live here so package code does not each reinvent the
same maintenance logic.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Maintainer Handbook"]
    section --> page["Quality Gates"]
    dest1["quality gates"]
    dest2["schema governance"]
    dest3["release support"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Quality Gates"]
    focus1["Maintainer role"]
    page --> focus1
    focus1_1["quality"]
    focus1 --> focus1_1
    focus1_2["security"]
    focus1 --> focus1_2
    focus2["Repository health"]
    page --> focus2
    focus2_1["schemas"]
    focus2 --> focus2_1
    focus2_2["supply chain"]
    focus2 --> focus2_2
    focus3["Operational outcome"]
    page --> focus3
    focus3_1["release clarity"]
    focus3 --> focus3_1
    focus3_2["package consistency"]
    focus3 --> focus3_2
```

## Current Quality Surfaces

- dependency analysis in `quality/deptry_scan.py`
- package-specific checks under `packages/`
- root test coverage through `packages/bijux-canon-dev/tests`

## What This Page Answers

- which repository maintenance concern this page explains
- which maintainer modules or tests support that concern
- what a reviewer should confirm before changing repository automation

## Purpose

This page explains how the package participates in repository-wide correctness and consistency.

## Stability

Keep it aligned with the actual quality checks that run in tests or CI.
