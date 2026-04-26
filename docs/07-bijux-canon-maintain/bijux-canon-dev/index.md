---
title: bijux-canon-dev
audience: mixed
type: index
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# bijux-canon-dev

`bijux-canon-dev` is the maintainer package for repository health. It exists
so schema drift checks, quality gates, supply-chain helpers, and release
support have one clear home outside the end-user product surface.

Hidden maintenance logic erodes trust fast. Repository policy should be
traceable to helper modules, tests, and documented integration points rather
than reconstructed from CI output or shell glue.

## Visual Summary

```mermaid
flowchart TB
    dev["bijux-canon-dev<br/>repository health helpers"]
    quality["quality<br/>deptry and repository policy checks"]
    security["security and sbom<br/>audit gates and requirements output"]
    schema["api governance<br/>freeze contracts and drift checks"]
    release["release support<br/>version and publication guards"]
    docs["docs support<br/>badge sync and mkdocs catalog logic"]
    dev --> quality
    dev --> security
    dev --> schema
    dev --> release
    dev --> docs
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
    class docs positive;
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
- open [SBOM and Supply Chain](sbom-and-supply-chain.md) when the concern is requirements output or provenance support
- open [Operating Guidelines](operating-guidelines.md) when the concern is safe maintainer use of these helpers

## Module Map

- `src/bijux_canon_dev/quality` for repository quality checks
- `src/bijux_canon_dev/security` for security gates
- `src/bijux_canon_dev/sbom` for supply-chain and bill-of-materials support
- `src/bijux_canon_dev/release` for release support
- `src/bijux_canon_dev/api` for OpenAPI and schema drift tooling
- `src/bijux_canon_dev/docs` for badge sync and docs catalog support
- `src/bijux_canon_dev/packages` for package-specific repository helpers

## Concrete Anchors

- `packages/bijux-canon-dev/src/bijux_canon_dev` for maintainer helpers
- `packages/bijux-canon-dev/tests` for executable maintenance proof
- `apis/` and root workflows for repository-level integration points

## Ownership Boundary

`bijux-canon-dev` owns repository-health helper code, not product behavior. If
the change would change ingest, index, reason, agent, or runtime semantics for
users, this section should stop at the integration point and hand the detail
back to the owning product package.

## Maintainer Standard

Each claimed maintenance rule should be visible in helper code, tests, or an
explicit integration surface such as `apis/`, `Makefile`, or
`.github/workflows/`. Hidden policy is still undocumented policy.
