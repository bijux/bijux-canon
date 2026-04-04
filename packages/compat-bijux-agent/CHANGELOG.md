# Changelog

All notable changes to `bijux-agent` are documented here.

This compatibility package exists to preserve the former agent distribution
name while the canonical package lives at `bijux-canon-agent`.

Historical release entries below preserve the wording that shipped with tagged
releases when a tagged changelog existed.

## Unreleased

- No package-local changes recorded yet.

## 0.3.0 - 2026-04-04

### Added

- Package-local release history for the compatibility distribution so legacy
  installs have an auditable migration record of their own.

### Changed

- Compatibility messaging now consistently points new work to
  `bijux-canon-agent` while preserving the legacy distribution, import, and
  command names.

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
