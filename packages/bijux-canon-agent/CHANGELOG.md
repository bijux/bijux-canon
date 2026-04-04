# Changelog

All notable changes to `bijux-canon-agent` are documented here.

Historical release entries below preserve the wording that shipped with the
tagged release.

## Unreleased

- PyPI metadata, keywords, and project URLs now make the canonical agent
  package easier to discover from package indexes and Bijux-owned docs.
- The package README now uses PyPI-safe badge and link targets, and it points
  legacy `bijux-agent` users to the canonical migration path and retired
  repository guidance.

## 0.3.0 - 2026-04-04

### Added

- Package-local maintainer docs now cover scope, architecture, boundaries,
  contracts, source-of-truth locations, and test strategy.

### Changed

- The package was realigned under the canonical `bijux-canon-agent` identity,
  including package names, public surfaces, and package-local docs.
- Boundary code was reorganized under explicit `interfaces/` and versioned
  `api/` packages, while orchestration moved under `application/`.
- Pipeline internals were decomposed into smaller modules for validation,
  critique, summarization, file reading, lifecycle control, convergence, LLM
  runtime support, and trace handling.
- Core support code was clarified around `contracts/`, `core/`, `llm/`, and
  `traces/` so ownership is easier to follow and maintain.

### Fixed

- CLI helper compatibility exports were restored after the module split work.
- Root package quality gates and documentation snapshot checks were repaired
  after the refactor series.

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
