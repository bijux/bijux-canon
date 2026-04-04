---
title: Scope and Non-Goals
audience: mixed
type: guide
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# Scope and Non-Goals

`bijux-canon-dev` is for maintainers and automation.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Maintainer Handbook"]
    section --> page["Scope and Non-Goals"]
    dest1["quality gates"]
    dest2["schema governance"]
    dest3["release support"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Scope and Non-Goals"]
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

## In Scope

- CI-facing helpers
- quality, security, SBOM, release, and schema checks
- package-specific repository automation

## Out of Scope

- user-facing runtime behavior
- product-domain models that belong to canonical packages
- legacy-name compatibility shims

## Purpose

This page prevents maintenance code from becoming an unbounded dumping ground.

## Stability

Update this page only when ownership truly moves into or out of the maintenance package.
