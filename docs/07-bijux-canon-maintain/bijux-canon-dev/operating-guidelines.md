---
title: Operating Guidelines
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# Operating Guidelines

Changes in `bijux-canon-dev` should be especially careful because they can
affect multiple packages at once.

That is why this section needs to be unusually honest. A small maintainer
change can carry wide consequences, so the package should bias toward
explicit scope, explicit tests, and explicit explanations.

## Visual Summary

```mermaid
flowchart LR
    change["Maintainer-surface change"]
    scope["Keep package impact explicit"]
    tests["Prefer testable helpers over opaque glue"]
    docs["Document maintainer-only behavior here"]
    change --> scope --> tests --> docs
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class change page;
    class scope positive;
    class tests anchor;
    class docs action;
```

## Guidelines

- prefer checks that are reviewable and testable over opaque shell glue
- keep repository automation explicit about which packages it touches
- document maintainer-only behavior in this section rather than in user-facing package pages

## Concrete Anchors

- `packages/bijux-canon-dev/src/bijux_canon_dev` for maintainer helpers
- `packages/bijux-canon-dev/tests` for executable maintenance proof
- `apis/` and root workflows for repository-level integration points

## Open This Page When

- you are changing repository automation, validation, or release support
- you need maintainer-only context that should not live in product package docs
- you are reviewing CI, schema drift, or supply-chain behavior

## Decision Rule

Use this page when the main need is understanding how maintainer changes should
be handled. If the change would affect end-user behavior directly, keep it in
the owning product package instead of treating maintainer automation as a
shortcut layer.

## What This Page Answers

- which working posture is expected for maintainer changes
- which maintainer modules or tests support that concern
- what a reviewer should confirm before changing repository automation

## Reviewer Lens

- compare the described maintainer behavior with the actual helper modules and tests
- check that maintainer-only guidance has not leaked into product-facing pages
- confirm that repository automation still names its package impact explicitly

## Next Checks

- open the package handbooks at `https://bijux.io/bijux-canon/02-bijux-canon-ingest/`
  through `https://bijux.io/bijux-canon/06-bijux-canon-runtime/` if the
  question is user-facing behavior rather than repository health
- open the relevant helper module or test after using this page to orient yourself
- return to the repository handbook at `https://bijux.io/bijux-canon/01-bijux-canon/`
  when the maintainer issue turns out to be root policy instead

## Honesty Boundary

This section can describe maintainer automation and repository health work, but
it should never imply that maintainer tooling is part of the end-user product
surface. Hidden scripts still need visible code, tests, and workflow context to
be trustworthy.

