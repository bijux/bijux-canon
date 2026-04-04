# Architecture

This package is intentionally utility-heavy and product-light.

## Main areas

- `quality/` contains helpers used by repository quality gates
- `security/` contains security-oriented checks and wrappers
- `sbom/` and `release/` contain metadata, dependency, and release support
- `api/` contains shared schema and OpenAPI maintenance helpers
- `packages/` contains maintenance logic that is specific to a package but still used through root automation

## Intended flow

1. Root `make` targets or CI decide which check should run.
2. The repository automation calls into a small, explicit helper in this package.
3. The helper reads repository state, performs the check, and emits a stable result.

## Design expectations

- prefer explicit Python entrypoints over opaque shell fragments
- make subprocess and filesystem effects obvious
- keep product packages free of duplicated repo-maintenance logic
- optimize for maintainability and clarity, not clever tooling tricks
