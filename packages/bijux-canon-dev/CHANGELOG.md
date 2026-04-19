# Changelog

All notable changes to `bijux-canon-dev` are documented here.

This package owns repository maintenance helpers, so its release history should
explain changes to shared tooling, publish support, security checks, and schema
governance.

## 0.3.6 - 2026-04-20

### Changed

- Prepared the `v0.3.6` release line by aligning fallback versions and inter-package dependency floors across the repository.
- Synchronized release automation and governance with the `bijux-std v0.1.3` shared standards baseline.

### Fixed

- `release-pypi.yml` now uses parse-safe publication gating for token/bootstrap checks.
- Protected workflow policy checks now accept shared-manifest-driven standards updates through approved control paths.

## 0.3.5 - 2026-04-19

### Changed

- Release metadata contracts now validate canonical package and API path usage
  in maintainer tests and generated repository documentation catalogs.
- Documentation navigation contracts were refreshed to assert current canonical
  handbook routes instead of legacy redirect entrypoints.

### Fixed

- Badge-template publication checks now reflect distinct release workflow badges
  for PyPI, GHCR, and GitHub release automation.

## 0.3.4 - 2026-04-11

### Changed

- Shared badge generation now treats `docs/badges.md` as the single source of
  truth for root, docs, and package README badge blocks.

### Fixed

- Release metadata contracts now enforce `0.3.4` as the current public package
  line.
- Documentation publication checks now lock GHCR badge targets to the
  user-scoped packages summary and exact package pages.

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
