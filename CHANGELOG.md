# Changelog

This file records notable repository-level changes for `bijux-canon`.

It does not replace the release history for individual packages. Package
versions, package tags, and package-specific release notes stay with the owning
distribution.

The goal of this changelog is to explain repository changes that affect more
than one package or change the way contributors and maintainers work across the
whole workspace.

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
