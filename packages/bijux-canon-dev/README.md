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
- compatibility shims whose only job is to preserve legacy package names

## Source map

- [`src/bijux_canon_dev/quality`](src/bijux_canon_dev/quality) for repo quality checks
- [`src/bijux_canon_dev/security`](src/bijux_canon_dev/security) for security gates
- [`src/bijux_canon_dev/sbom`](src/bijux_canon_dev/sbom) for bill-of-materials generation
- [`src/bijux_canon_dev/release`](src/bijux_canon_dev/release) for release support
- [`src/bijux_canon_dev/api`](src/bijux_canon_dev/api) for OpenAPI and schema tooling
- [`src/bijux_canon_dev/packages`](src/bijux_canon_dev/packages) for package-specific maintenance helpers
- [`tests`](tests) for executable protection of repo tooling behavior

## Read this next

- [Package guide](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/)
- [Scope and non-goals](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/scope-and-non-goals/)
- [Module map](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/module-map/)
- [Quality gates](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/quality-gates/)
- [Release support](https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/release-support/)
- [Changelog](CHANGELOG.md)
