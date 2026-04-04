---
title: Release Support
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# Release Support

Shared release helpers belong here so versioning and packaging practices stay
consistent across the repository.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Maintainer Handbook"]
    section --> page["Release Support"]
    dest1["quality gates"]
    dest2["schema governance"]
    dest3["release support"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Release Support"]
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

- `release/version_resolver.py`
- package metadata checks in tests
- root commit conventions configured through commitizen

## Concrete Anchors

- `packages/bijux-canon-dev/src/bijux_canon_dev` for maintainer helpers
- `packages/bijux-canon-dev/tests` for executable maintenance proof
- `apis/` and root workflows for repository-level integration points

## Use This Page When

- you are changing repository automation, validation, or release support
- you need maintainer-only context that should not live in product package docs
- you are reviewing CI, schema drift, or supply-chain behavior

## What This Page Answers

- which repository maintenance concern this page explains
- which maintainer modules or tests support that concern
- what a reviewer should confirm before changing repository automation

## Reviewer Lens

- compare the described maintainer behavior with the actual helper modules and tests
- check that maintainer-only guidance has not leaked into product-facing pages
- confirm that repository automation still names its package impact explicitly

## Honesty Boundary

This section can describe maintainer automation and repository health work, but it should never imply that maintainer tooling is part of the end-user product surface.

## Purpose

This page records the maintenance package role in release preparation.

## Stability

Keep it aligned with the real release support code and the actual versioning workflow.

## Core Claim

Each maintainer page should explain repository-health behavior in a way that is explicit, testable, and clearly separate from end-user product behavior.

## Why It Matters

Maintainer pages matter because hidden automation is one of the fastest ways for a monorepo to become hard to trust, hard to change, and hard to release safely.

## If It Drifts

- maintainer-only behavior becomes harder to discover before it surprises a contributor
- repository automation changes without a stable explanation of its intent
- product docs get polluted with infrastructure concerns that belong elsewhere
