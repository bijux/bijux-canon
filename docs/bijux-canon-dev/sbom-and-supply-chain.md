---
title: SBOM and Supply Chain
audience: mixed
type: guide
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# SBOM and Supply Chain

Supply-chain visibility is a repository maintenance concern, so SBOM helpers
live in `bijux-canon-dev` instead of being duplicated by each package.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Maintainer Handbook"]
    section --> page["SBOM and Supply Chain"]
    dest1["quality gates"]
    dest2["schema governance"]
    dest3["release support"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["SBOM and Supply Chain"]
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

## Current Surfaces

- `sbom/requirements_writer.py`
- `tests/test_sbom_requirements_writer.py`
- shared dependency metadata in package `pyproject.toml` files

## What This Page Answers

- which repository maintenance concern this page explains
- which maintainer modules or tests support that concern
- what a reviewer should confirm before changing repository automation

## Purpose

This page explains the home for supply-chain oriented repository tooling.

## Stability

Keep it aligned with the checked-in SBOM helpers and tests.
