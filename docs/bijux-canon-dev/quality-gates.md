---
title: Quality Gates
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# Quality Gates

Repository quality checks live here so package code does not each reinvent the
same maintenance logic.

This page should make the gates feel concrete and inspectable. A quality bar
is more credible when a contributor can point to the helper, the test, and
the workflow that back it.

These maintainer pages should read like explicit operational memory for repository-health work. They are strongest when they expose automation intent, package impact, and repository policy without pretending that CI logs are documentation.

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Maintainer Handbook"]
    section --> page["Quality Gates"]
    dest1["explain automation"]
    dest2["see repository-health scope"]
    dest3["review package impact"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Quality Gates"]
    focus1["Maintainer role"]
    page --> focus1
    focus1_1["quality gates"]
    focus1 --> focus1_1
    focus1_2["security gates"]
    focus1 --> focus1_2
    focus2["Repository health"]
    page --> focus2
    focus2_1["schema integrity"]
    focus2 --> focus2_1
    focus2_2["supply-chain visibility"]
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

## Concrete Anchors

- `packages/bijux-canon-dev/src/bijux_canon_dev` for maintainer helpers
- `packages/bijux-canon-dev/tests` for executable maintenance proof
- `apis/` and root workflows for repository-level integration points

## Use This Page When

- you are changing repository automation, validation, or release support
- you need maintainer-only context that should not live in product package docs
- you are reviewing CI, schema drift, or supply-chain behavior

## Decision Rule

Use `Quality Gates` to decide whether a change belongs to maintainer automation or to a product package contract. If the change would affect end-user behavior directly, this page should push the review back toward the owning product package instead of letting maintainer scope sprawl.

## What This Page Answers

- which repository maintenance concern this page explains
- which maintainer modules or tests support that concern
- what a reviewer should confirm before changing repository automation

## Reviewer Lens

- compare the described maintainer behavior with the actual helper modules and tests
- check that maintainer-only guidance has not leaked into product-facing pages
- confirm that repository automation still names its package impact explicitly

## Next Checks

- move to product package docs if the question is user-facing behavior rather than repository health
- open the relevant helper module or test after using this page to orient yourself
- return to repository handbook pages when the maintainer issue turns out to be root policy instead

## Honesty Boundary

This section can describe maintainer automation and repository health work, but it should never imply that maintainer tooling is part of the end-user product surface. It also should not pretend that hidden scripts count as documentation just because CI happens to run them.

## Purpose

This page explains how the package participates in repository-wide correctness and consistency.

## Stability

Keep it aligned with the actual quality checks that run in tests or CI.
