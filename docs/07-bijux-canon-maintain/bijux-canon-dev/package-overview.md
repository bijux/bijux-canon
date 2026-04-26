---
title: Package Overview
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# Package Overview

`bijux-canon-dev` is intentionally not part of the end-user runtime. It is
the package that keeps the monorepo honest when schemas drift, security
tooling falls behind, or release metadata becomes inconsistent.

A good maintainer package should reduce mystery, not create a new layer of
it. The automation belongs here because it serves repository health across
packages rather than product behavior inside one package.

## Visual Summary

```mermaid
flowchart LR
    dev["bijux-canon-dev<br/>maintainer-only runtime"]
    helpers["Shared helpers for repo health"]
    schemas["Schema and metadata integrity"]
    release["Release support and version checks"]
    product["Not product-domain behavior"]
    dev --> helpers
    dev --> schemas
    dev --> release
    dev --> product
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class dev page;
    class helpers positive;
    class schemas anchor;
    class release action;
    class product caution;
```

## What It Owns

- shared quality and security helpers used across packages
- release, versioning, and SBOM helpers
- OpenAPI and schema drift tooling
- package-specific maintenance helpers invoked by root automation

## Concrete Anchors

- `packages/bijux-canon-dev/src/bijux_canon_dev` for maintainer helpers
- `packages/bijux-canon-dev/tests` for executable maintenance proof
- `apis/` and root workflows for repository-level integration points

## Open This Page When

- you are changing repository automation, validation, or release support
- you need maintainer-only context that should not live in product package docs
- you are reviewing CI, schema drift, or supply-chain behavior

## Decision Rule

This page answers one question: whether a change belongs in maintainer
automation or in a product package contract. If the change would affect
end-user behavior directly, open the owning product package instead of
letting maintainer scope sprawl.

## What You Can Resolve Here

- which repository-health concerns `bijux-canon-dev` owns
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
surface. Hidden scripts still need visible code, tests, and workflow context to
be trustworthy.

