---
title: Schema Governance
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# Schema Governance

The package owns repository-level helpers that keep API schemas and tracked
schema artifacts synchronized with the code that claims to implement them.

Schema drift is one of the easiest ways to lose user trust quietly. This
section shows where the repository checks that risk and why that work belongs
in maintainer tooling.

## Visual Summary

```mermaid
flowchart LR
    code["API implementation changes"]
    schema["Tracked schema artifacts"]
    drift["OpenAPI drift helper"]
    review["Review the contract delta"]
    code --> schema --> drift --> review
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class code page;
    class schema anchor;
    class drift positive;
    class review action;
```

## Current Surfaces

- `api/openapi_drift.py`
- tests such as `tests/test_openapi_drift.py`
- root `apis/` directories that store reviewed schema artifacts

## Concrete Anchors

- `packages/bijux-canon-dev/src/bijux_canon_dev` for maintainer helpers
- `packages/bijux-canon-dev/tests` for executable maintenance proof
- `apis/` and root workflows for repository-level integration points

## Open This Page When

- you are changing repository automation, validation, or release support
- you need maintainer-only context that should not live in product package docs
- you are reviewing CI, schema drift, or supply-chain behavior

## Decision Rule

This page shows how schema drift is checked and
reviewed across the repository. If the change would affect end-user behavior
directly, open the owning product package instead.

## What You Can Resolve Here

- which schema-governance checks live in `bijux-canon-dev`
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
surface. Schema claims still need visible helpers, tests, tracked artifacts,
and workflow context to be trustworthy.

