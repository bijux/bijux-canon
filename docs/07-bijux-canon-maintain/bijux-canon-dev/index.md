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

Hidden maintenance logic erodes trust fast. Repository policy belongs in
helper modules, tests, and documented integration points instead of being
reconstructed from CI output or shell glue.

## Pages In This Handbook

- [Package Overview](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/package-overview/)
- [Scope and Non-Goals](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/scope-and-non-goals/)
- [Module Map](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/module-map/)
- [Quality Gates](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/quality-gates/)
- [Security Gates](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/security-gates/)
- [Schema Governance](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/schema-governance/)
- [Release Support](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/release-support/)
- [SBOM and Supply Chain](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/sbom-and-supply-chain/)
- [Operating Guidelines](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/operating-guidelines/)

## Open This Handbook When

- the concern is inside the maintainer helper package itself
- you need to understand which helper module or quality surface enforces a
  repository-health rule
- the question is about schema drift, release support, quality gates, or
  supply-chain tooling

## Open Another Handbook When

- the question is really about a product package API, CLI, or runtime contract
- the issue belongs to shared Make entrypoints or GitHub Actions trigger logic
- you are looking for end-user behavior rather than repository-health helpers

## Start Here

- open [Package Overview](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/package-overview/) for the shortest description of
  why this maintainer package exists
- open [Module Map](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/module-map/) when you need the concrete helper-module
  layout
- open [Quality Gates](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/quality-gates/) or [Security Gates](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/security-gates/)
  when the question is about policy enforcement
- open [Schema Governance](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/schema-governance/) or
  [Release Support](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/release-support/) when the question is about repository
  publication discipline
- open [SBOM and Supply Chain](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/sbom-and-supply-chain/) when the concern is requirements output or provenance support
- open [Operating Guidelines](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/operating-guidelines/) when the concern is safe maintainer use of these helpers

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
the change would alter ingest, index, reason, agent, or runtime semantics for
users, this section should stop at the integration point and hand the detail
back to the owning product package.

## Maintainer Standard

Each claimed maintenance rule belongs in helper code, tests, or an explicit
integration surface such as `apis/`, `Makefile`, or
`.github/workflows/`. Hidden policy is still undocumented policy.
