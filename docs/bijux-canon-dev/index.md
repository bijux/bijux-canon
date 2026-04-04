---
title: Maintainer Handbook
audience: mixed
type: index
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# Maintainer Handbook

`bijux-canon-dev` is the maintainer package for repository health. It exists
so schema drift checks, quality gates, supply-chain helpers, and release
support have one clear home outside the end-user product surface.

This package matters because hidden maintenance logic erodes trust fast. If
contributors can only discover repository policy by reading CI output or shell
glue, the monorepo stops feeling reviewable.

These maintainer pages should read like explicit operational memory for repository-health work. They are strongest when they expose automation intent, package impact, and repository policy without pretending that CI logs are documentation.

## Visual Summary

```mermaid
flowchart RL
    page["Maintainer Handbook<br/>clarifies: explain automation | see repository-health scope | review package impact"]
    classDef page fill:#dbeafe,stroke:#1d4ed8,color:#1e3a8a,stroke-width:2px;
    classDef positive fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef caution fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef anchor fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    classDef action fill:#fef3c7,stroke:#d97706,color:#7c2d12;
    role1["release support"]
    role1 --> page
    role2["quality gates"]
    role2 --> page
    role3["security gates"]
    role3 --> page
    health1["supply-chain visibility"]
    page --> health1
    health2["package-aware automation"]
    page --> health2
    health3["schema integrity"]
    page --> health3
    outcome1["package consistency"]
    health1 --> outcome1
    outcome2["less CI archaeology"]
    health2 --> outcome2
    outcome3["release clarity"]
    health3 --> outcome3
    class page page;
    class role1,role2,role3 positive;
    class health1,health2,health3 anchor;
    class outcome1,outcome2,outcome3 action;
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

## Use This Page When

- you are changing repository automation, validation, or release support
- you need maintainer-only context that should not live in product package docs
- you are reviewing CI, schema drift, or supply-chain behavior

## Decision Rule

Use `Maintainer Handbook` to decide whether a change belongs to maintainer automation or to a product package contract. If the change would affect end-user behavior directly, this page should push the review back toward the owning product package instead of letting maintainer scope sprawl.

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

This page explains how to use the maintainer handbook without confusing it with user-facing product docs.

## Stability

Keep this page aligned with the actual maintainer modules that exist under `packages/bijux-canon-dev`.
