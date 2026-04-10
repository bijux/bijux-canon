# Changelog

All notable changes to `bijux-canon-dev` are documented here.

This package owns repository maintenance helpers, so its release history should
explain changes to shared tooling, publish support, security checks, and schema
governance.

## 0.3.2 - 2026-04-10

### Fixed

- Release metadata contracts now enforce the public package fallback version
  expected for the `v0.3.2` release line.
- Package release-surface documentation checks now cover the current
  per-package PyPI guidance.

## 0.3.0 - 2026-04-05

### Added

- Package-local documentation for release support, schema governance, SBOM
  generation, operating guidelines, and quality/security gates.
- A package-local changelog so maintainer tooling releases now have their own
  durable history instead of being implied through root changes alone.

### Changed

- Repository-owned tooling is now described as a publishable package with its
  own release story, rather than as anonymous root-only scripts.
- Release publish checks now resolve the same effective version Hatch builds,
  refuse accidental prerelease uploads by default, and verify built artifact
  versions before upload.
- The developer tooling lint target now honors the package-level decision to
  skip mypy in lint runs, instead of accidentally invoking the repository-wide
  strict type sweep for internal maintenance helpers.

### Fixed

- The developer tooling test environment now declares `hatch` explicitly
  because release-version validation executes Hatch inside tox environments.
- The developer tooling lint environment now declares `pydantic` explicitly so
  the repository-wide mypy plugin contract loads consistently inside tox.
- The developer tooling lint environment now declares `codespell` explicitly so
  the enabled lint toolchain is fully present inside tox runs.
- The dev package quality contract now treats intentional cross-package helper
  imports as repository-internal tooling instead of missing product
  dependencies, and the package files were reformatted to match the enforced
  Ruff baseline.
