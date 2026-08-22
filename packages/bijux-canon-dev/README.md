# bijux-canon-dev

`bijux-canon-dev` is the maintenance package for the monorepo itself. It holds
the Python helpers behind root quality gates, security checks, SBOM generation,
release support, OpenAPI drift checks, and package-specific repository
automation.

This package is for maintainers, CI, and root `make` targets. It is not part of
the end-user product surface. When a script or helper exists to keep the
repository healthy rather than to run the product, it should usually live here.

## What this package owns

- shared quality and security helpers used across packages
- release, versioning, and SBOM helpers
- OpenAPI and schema drift tooling
- package-specific repository maintenance helpers invoked by root automation

## What this package does not own

- runtime or product behavior that end users depend on directly
- domain models that belong to agent, ingest, index, reason, or runtime packages
- compatibility bridges whose only job is to preserve older or shorter public names

## How maintenance decisions flow

| Boundary | Responsibility | Evidence returned |
| --- | --- | --- |
| `bijux_canon_dev` helper | interpret one repository-specific invariant | structured result, rendered diagnostic, and exit status |
| Make target | supply environment, paths, and command composition | command log and artifacts under the repository artifact tree |
| GitHub workflow | select event, permissions, matrix, and retention | immutable workflow run and uploaded evidence |
| release workflow | bind a tag to validated distributions and destination | registry or release identity for the accepted artifact |

The helper should own a policy only when the rule spans repository structure or
needs reusable parsing and tests. Product behavior stays with the package that
implements it; Make remains command composition; workflows remain remote
enforcement. Moving a failure between those layers to obtain a green result
would destroy the diagnostic boundary.

## Distribution posture

`bijux-canon-dev` is an internal workspace support package. It is deliberately
excluded from the repository's public release package set. Its installed
maintenance commands verify supply-chain bindings, wheel metadata and contents,
and the complete supported Python wheel matrix; generated reports and isolated
environments belong under the repository `artifacts/` tree. Its VCS-derived
version supports workspace builds; it is not a promise of an end-user product
release.

## System Integration Evidence

Repository gates establish many independent contracts: package-local behavior,
schema and documentation consistency, dependency policy, build metadata,
compatibility alias identity, and release eligibility. They do not currently
include an installed-package lane that resolves and executes all four live
runtime integrations against the canonical agent, ingest, index, and reason
packages.

Runtime tests exercise execution, verification, replay, and failure semantics
by supplying test callables for those seams. That is valid evidence for the
runtime protocol, but it is not evidence that the canonical package roots
provide the required `run`, `retrieve`, `enforce_contract`, and `reason`
adapters. A coherent release can therefore pass package and bridge checks while
live system composition remains unproven.

The integration test belongs with runtime because runtime owns the adapter
protocol and normalized records. Repository maintenance should make that lane
visible, run it against installed release candidates, and retain its result;
maintenance code should not manufacture product adapters or weaken domain
contracts to make the lane pass.

## Source map

- [`src/bijux_canon_dev/quality`](src/bijux_canon_dev/quality) for repo quality checks
- [`src/bijux_canon_dev/security`](src/bijux_canon_dev/security) for security gates
- [`src/bijux_canon_dev/sbom`](src/bijux_canon_dev/sbom) for bill-of-materials generation
- [`src/bijux_canon_dev/release`](src/bijux_canon_dev/release) for release support
- [`src/bijux_canon_dev/api`](src/bijux_canon_dev/api) for OpenAPI and schema tooling
- [`src/bijux_canon_dev/corpus`](src/bijux_canon_dev/corpus) for real-corpus review tooling
- [`src/bijux_canon_dev/packages`](src/bijux_canon_dev/packages) for package-specific maintenance helpers
- [`tests`](tests) for executable protection of repo tooling behavior

## Read this next

- [Package guide](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/)
- [Scope and non-goals](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/scope-and-non-goals/)
- [Module map](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/module-map/)
- [Quality gates](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/quality-gates/)
- [Release support](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/release-support/)
- [Changelog](CHANGELOG.md)
