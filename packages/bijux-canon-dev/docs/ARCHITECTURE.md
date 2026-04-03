# ARCHITECTURE

`bijux-canon-dev` is a repository tooling package.

Core layout:
- `src/bijux_canon_dev/quality/` owns repository quality helpers
- `src/bijux_canon_dev/security/` owns security gate helpers
- `src/bijux_canon_dev/sbom/` and `release/` own package metadata export and version resolution
- `src/bijux_canon_dev/api/` owns shared OpenAPI maintenance helpers
- `src/bijux_canon_dev/packages/` owns package-specific maintenance adapters

The architecture is intentionally adapter-heavy and product-light. This package exists to support the monorepo, not to become an application runtime.
