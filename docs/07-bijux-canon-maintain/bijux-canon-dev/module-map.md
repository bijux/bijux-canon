---
title: Module Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# Module Map

- `src/bijux_canon_dev/quality` for repository quality checks
- `src/bijux_canon_dev/security` for security gates
- `src/bijux_canon_dev/sbom` for supply-chain and bill-of-materials support
- `src/bijux_canon_dev/release` for release support
- `src/bijux_canon_dev/api` for OpenAPI and schema drift tooling
- `src/bijux_canon_dev/packages` for package-specific repository helpers

Read this page as a map of repository-health responsibilities. It should let
a contributor find the right maintenance code path without guessing whether
the behavior is about quality, security, schema governance, release work, or
supply-chain support.

These maintainer pages should read like explicit operational memory for repository-health work. They are strongest when they expose automation intent, package impact, and repository policy without pretending that CI logs are documentation.

## Visual Summary

```mermaid
flowchart LR
    page["Module Map<br/>clarifies: explain automation | see repository-health scope | review package impact"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    detail1["supply-chain visibility"]
    detail1 --> page
    detail2["package-aware automation"]
    detail2 --> page
    detail3["release clarity"]
    detail3 --> page
    detail4["package consistency"]
    detail4 --> page
    detail5["less CI archaeology"]
    detail5 --> page
    detail6["quality gates"]
    detail6 --> page
    detail7["security gates"]
    detail7 --> page
    detail8["release support"]
    detail8 --> page
    detail9["schema integrity"]
    detail9 --> page
    next1["return to repository handbook pages when the maintainer issue turns out to be root policy instead"]
    page --> next1
    next2["move to product package docs if the question is user-facing behavior rather than repository health"]
    page --> next2
    next3["open the relevant helper module or test after using this page to orient yourself"]
    page --> next3
    class page page;
    class detail1,detail2,detail3,detail4,detail5,detail6,detail7,detail8,detail9 anchor;
    class next1,next2,next3 action;
```

## Concrete Anchors

- `packages/bijux-canon-dev/src/bijux_canon_dev` for maintainer helpers
- `packages/bijux-canon-dev/tests` for executable maintenance proof
- `apis/` and root workflows for repository-level integration points

## Use This Page When

- you are changing repository automation, validation, or release support
- you need maintainer-only context that should not live in product package docs
- you are reviewing CI, schema drift, or supply-chain behavior

## Decision Rule

Use `Module Map` to decide whether a change belongs to maintainer automation or to a product package contract. If the change would affect end-user behavior directly, this page should push the review back toward the owning product package instead of letting maintainer scope sprawl.

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

This page is the shortest code-navigation aid for `bijux-canon-dev`.

## Stability

Keep it aligned with actual package modules and remove retired directories promptly.
