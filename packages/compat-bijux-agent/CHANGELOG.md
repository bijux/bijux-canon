# Changelog

All notable changes to `bijux-agent` are documented here.

This compatibility package exists to preserve the former agent distribution
name while the canonical package lives at `bijux-canon-agent`.

Historical release entries below preserve the wording that shipped with tagged
releases when a tagged changelog existed.

## 0.3.0 - 2026-04-05

### Added

- Package-local release history for the compatibility distribution so legacy
  installs have an auditable migration record of their own.

### Changed

- Compatibility messaging now consistently points new work to
  `bijux-canon-agent` while preserving the legacy distribution, import, and
  command names.
- PyPI metadata now points legacy `bijux-agent` readers at the canonical
  `bijux-canon-agent` docs, migration guide, and Bijux-owned package family.
- The package README and overview now document the retired standalone
  repository and use PyPI-safe badge and link targets.
- Package-local PyPI publication guidance is now checked in and shipped with
  the source distribution so legacy agent release expectations stay attached to
  the compatibility package.
- The published docs URL for `bijux-agent` now has its own migration landing
  page inside the shared handbook instead of sending legacy readers directly to
  canonical agent docs without context.

### Fixed

- Release artifacts now ship the repository license and publish package-local
  ignore rules instead of leaking repo-wide ignore policy into the source
  distribution.

## v0.1.0 (first public release)

- First public, contract-complete release of Bijux Agent.
- Deterministic execution with replayable artifacts and provenance.
- Non-deterministic exploration via structured randomness reports and convergence audits.
- CLI and orchestration surfaces frozen; trace schema versioned.
- Provenance, determinism, and execution ABI enforced via conformance tests.
- Agent execution kernel, lifecycle invariants, and passive-agent enforcement.
- Trace schema versioning, migration guards, and runtime compatibility checks.
- Convergence strategies and dry-run trace generator for deterministic tests.
- Reference pipelines, public API boundary docs, and star-import invariants.
