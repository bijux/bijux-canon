---
title: Maintenance Handbook
audience: mixed
type: index
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Maintenance Handbook

`bijux-canon-dev` is the maintainer package for repository health. It exists
so schema drift checks, quality gates, supply-chain helpers, and release
support have one clear home outside the end-user product surface.

This package matters because hidden maintenance logic erodes trust fast. If
contributors can only discover repository policy by reading CI output or shell
glue, the monorepo stops feeling reviewable.

These maintainer pages should read like explicit operational memory for repository-health work. They are strongest when they expose automation intent, package impact, and repository policy without pretending that CI logs are documentation.

## Visual Summary

```mermaid
flowchart LR
    dev["bijux-canon-dev<br/>repository health helpers"]
    quality["Quality and dependency checks"]
    security["Security and supply-chain checks"]
    schema["Schema drift and API governance"]
    release["Release and version support"]
    dev --> quality
    dev --> security
    dev --> schema
    dev --> release
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class dev page;
    class quality positive;
    class security caution;
    class schema anchor;
    class release action;
```

## Pages in This Section

- [Package Overview](package-overview.md)
- [Scope and Non-Goals](scope-and-non-goals.md)
- [Module Map](module-map.md)
- [Quality Gates](quality-gates.md)
- [Security Gates](security-gates.md)
- [Schema Governance](schema-governance.md)
- [Release Support](release-support.md)
- [SBOM and Supply Chain](sbom-and-supply-chain.md)
- [Operating Guidelines](operating-guidelines.md)

## Use This Section When

- the concern is inside the maintainer helper package itself
- you need to understand which helper module or quality surface enforces a
  repository-health rule
- the question is about schema drift, release support, quality gates, or
  supply-chain tooling

## Do Not Use This Section When

- the question is really about a product package API, CLI, or runtime contract
- the issue belongs to shared Make entrypoints or GitHub Actions trigger logic
- you are looking for end-user behavior rather than repository-health helpers

## Choose The Next Page By Question

- open [Package Overview](package-overview.md) for the shortest description of
  why this maintainer package exists
- open [Module Map](module-map.md) when you need the concrete helper-module
  layout
- open [Quality Gates](quality-gates.md) or [Security Gates](security-gates.md)
  when the question is about policy enforcement
- open [Schema Governance](schema-governance.md) or
  [Release Support](release-support.md) when the question is about repository
  publication discipline

## Module Map

- `src/bijux_canon_dev/quality` for repository quality checks
- `src/bijux_canon_dev/security` for security gates
- `src/bijux_canon_dev/sbom` for supply-chain and bill-of-materials support
- `src/bijux_canon_dev/release` for release support
- `src/bijux_canon_dev/api` for OpenAPI and schema drift tooling
- `src/bijux_canon_dev/packages` for package-specific repository helpers

## Concrete Anchors

- `packages/bijux-canon-dev/src/bijux_canon_dev` for maintainer helpers
- `packages/bijux-canon-dev/tests` for executable maintenance proof
- `apis/` and root workflows for repository-level integration points

## Reader Takeaway

Use `bijux-canon-dev` when the repository-health concern is implemented as
helper code. If the question is really about shared command routing or workflow
triggering, move sideways to `makes/` or `gh-workflows/` instead.

## Use This Page When

- you are changing repository automation, validation, or release support
- you need maintainer-only context that should not live in product package docs
- you are reviewing CI, schema drift, or supply-chain behavior

## Decision Rule

Use `Maintenance Handbook` to decide whether a change belongs to maintainer automation or to a product package contract. If the change would affect end-user behavior directly, this page should push the review back toward the owning product package instead of letting maintainer scope sprawl.

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

This page explains how to use the maintenance handbook without confusing it with user-facing product docs.

## Stability

Keep this page aligned with the actual maintainer modules that exist under `packages/bijux-canon-dev`.
