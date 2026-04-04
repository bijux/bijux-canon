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
