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

A quality bar is more credible when a contributor can point to the helper, the
test, and the workflow that back it.

## Visual Summary

```mermaid
flowchart LR
    change["Shared change"]
    scan["Dependency and quality scans"]
    package["Package-specific checks"]
    tests["Maintainer tests prove the helper"]
    change --> scan --> package --> tests
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class change page;
    class scan positive;
    class package anchor;
    class tests action;
```

## Current Quality Surfaces

- dependency analysis in `quality/deptry_scan.py`
- package-specific checks under `packages/`
- root test coverage through `packages/bijux-canon-dev/tests`

## Concrete Anchors

- `packages/bijux-canon-dev/src/bijux_canon_dev` for maintainer helpers
- `packages/bijux-canon-dev/tests` for executable maintenance proof
- `apis/` and root workflows for repository-level integration points

## Open This Page When

- you are changing repository automation, validation, or release support
- you need maintainer-only context that should not live in product package docs
- you are reviewing CI, schema drift, or supply-chain behavior

## Decision Rule

Use this page when the main question is how repository-wide quality checks are
implemented and reviewed. If the change would affect end-user behavior
directly, open the owning product package instead.

## What You Can Resolve Here

- which repository-wide quality checks live in `bijux-canon-dev`
- which maintainer modules or tests support that concern
- what a reviewer should confirm before changing repository automation

## Review Focus

- compare the described maintainer behavior with the actual helper modules and tests
- check that maintainer-only guidance has not leaked into product-facing pages
- confirm that repository automation still names its package impact explicitly

## Read Next

- open the package handbooks at `https://bijux.io/bijux-canon/02-bijux-canon-ingest/`
  through `https://bijux.io/bijux-canon/06-bijux-canon-runtime/` if the
  question is user-facing behavior rather than repository health
- open the relevant helper module or test after using this page to orient yourself
- return to the repository handbook at `https://bijux.io/bijux-canon/01-bijux-canon/`
  when the maintainer issue turns out to be root policy instead

## Limits

This section can describe maintainer automation and repository health work, but
it should never imply that maintainer tooling is part of the end-user product
surface. Quality claims still need visible helpers, tests, and workflow context
to be trustworthy.

