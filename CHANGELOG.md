# Changelog

This file records notable repository-level changes for `bijux-canon`.

It does not replace the release history for individual packages. Package
versions, package tags, and package-specific release notes stay with the owning
distribution.

The goal of this changelog is to explain repository changes that affect more
than one package or change the way contributors and maintainers work across the
whole workspace.

## 0.3.6 - Unreleased

### Changed

- Prepared repository-level release notes for the `0.3.6` line and aligned maintainer-facing README release-readiness guidance with changelog ownership.

## 0.3.5 - 2026-04-19

### Changed

- Repository badge templates now publish dedicated workflow badges for
  `release-pypi.yml`, `release-ghcr.yml`, and `release-github.yml` across the
  README and docs landing surfaces.
- Release readiness and docs contracts were aligned with canonical package/API
  paths and current handbook routes.

### Fixed

- Shared standards manifests, workflow inventory references, and generated docs
  catalogs now consistently point at canonical `packages/bijux-canon-*` and
  `apis/bijux-canon-*` locations.
- Compatibility handbook links now resolve canonical package handbook URLs
  without stale numbered slug targets.

## 0.3.4 - 2026-04-11

### Changed

- Shared badge generation now treats `docs/badges.md` as the single source of
  truth for the root README, the docs landing page, and every public package
  README.
- Repository release notes now describe GHCR publication through exact package
  pages instead of a vague family placeholder path.

### Fixed

- GHCR badge targets now consistently use the user-scoped GitHub Packages
  summary page and exact package pages for canonical and compatibility
  distributions.
- Public package fallback versions, runtime dependency floors, and maintainer
  release checks now align with the synchronized `v0.3.4` release line.

## 0.3.3 - 2026-04-10

### Changed

- Public package fallback versions and runtime dependency floors now align with
  the synchronized `v0.3.3` canon release line.
- Source-checkout version fallbacks and repository release tests now target
  `0.3.3` as the current public release version.

## 0.3.2 - 2026-04-10

### Fixed

- Public package fallback versions now align with the `v0.3.2` release tag
  across canonical and compatibility distributions.
- Runtime package dependency floors now require the synchronized `0.3.2`
  canon package line.
- Source-checkout version fallbacks now report the intended release version
  when installed package metadata is unavailable.
- Developer release contracts now check the current public fallback version and
  package release-surface documentation.

## 0.3.0 - 2026-04-05

### Added

- Repository handbooks now cover workspace layout, package mapping, API schema
  governance, release/versioning rules, and documentation-system ownership in
  one maintainers-first navigation surface.
- Compatibility-package handbook pages now explain preserved legacy names,
  migration guidance, validation expectations, and retirement criteria.

### Changed

- Release guidance now states that every publishable package owns its own
  `CHANGELOG.md`, while this root file only records repository-wide work.
- Repository docs now describe commit messages as durable release history, so
  future maintainers can understand intent without diff-mining old changes.

## Changelog Scope

Use this file for changes such as:

- root governance and contributor policy
- shared automation under `makes/`
- shared configuration under `configs/`
- root handbook and repository navigation
- repository-level CI, publish, and release process changes
- shared API artifact conventions under `apis/`

Do not use this file for changes that only affect one package release stream
unless the repository-level workflow changed too.
