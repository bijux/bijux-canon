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

Read this page as a map of repository-health responsibilities. It lets
a contributor find the right maintenance code path without guessing whether
the behavior is about quality, security, schema governance, release work, or
supply-chain support.

## Visual Summary

```mermaid
flowchart LR
    quality["quality/<br/>dependency and repository checks"]
    security["security/<br/>audit gates"]
    schema["api/<br/>schema drift helpers"]
    release["release/<br/>version and publication support"]
    packages["packages/<br/>package-specific helpers"]
    quality --> schema
    security --> schema
    schema --> release
    release --> packages
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class quality positive;
    class security caution;
    class schema page;
    class release action;
    class packages anchor;
```

## Concrete Anchors

- `packages/bijux-canon-dev/src/bijux_canon_dev` for maintainer helpers
- `packages/bijux-canon-dev/tests` for executable maintenance proof
- `apis/` and root workflows for repository-level integration points

## Open This Page When

- you are changing repository automation, validation, or release support
- you need maintainer-only context that should not live in product package docs
- you are reviewing CI, schema drift, or supply-chain behavior

## Decision Rule

Use this page when the main need is finding the maintainer module that owns a
repository-health concern. If the change would affect end-user behavior
directly, open the owning product package instead.

## What This Page Answers

- which maintainer module owns which repository-health concern
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

