# Changelog

All notable changes to `bijux-canon-dev` are documented here.

This package owns repository maintenance helpers, so its release history should
explain changes to shared tooling, publish support, security checks, and schema
governance.

## Unreleased

- Release publish checks now resolve the same effective version Hatch builds,
  refuse accidental prerelease uploads by default, and verify built artifact
  versions before upload.

## 0.3.0 - 2026-04-04

### Added

- Package-local documentation for release support, schema governance, SBOM
  generation, operating guidelines, and quality/security gates.
- A package-local changelog so maintainer tooling releases now have their own
  durable history instead of being implied through root changes alone.

### Changed

- Repository-owned tooling is now described as a publishable package with its
  own release story, rather than as anonymous root-only scripts.
