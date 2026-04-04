Owner: Bijan Mousavi
Status: stable
Scope: Changelog.

# Changelog

All notable changes to this project are documented here. This file is generated via towncrier; do not edit by hand.

Historical release entries below preserve the wording that shipped with the
tagged release.

## Unreleased

### Added

- Package-local documentation now explains scope, architecture, boundaries,
  contracts, and test strategy in maintainer-facing language.

### Changed

- The package was realigned under the canonical `bijux-canon-agent` identity,
  with module names, package surfaces, and docs updated to match durable
  ownership.
- CLI and HTTP boundaries were reorganized under explicit `interfaces/` and
  versioned `api/` packages.
- Pipeline internals were split into smaller modules for validation, critique,
  summarization, file reading, lifecycle control, convergence, and trace
  handling.

### Fixed

- Root package quality gates were restored after the refactor series, including
  compatibility exports needed by CLI helpers.

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
