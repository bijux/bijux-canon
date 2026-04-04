# Changelog

All notable changes to `bijux-canon-index` are documented here.

Historical release entries below preserve the wording that shipped with the
tagged release, including legacy distribution naming where applicable.

## Unreleased

- No package-local changes recorded yet.

## 0.3.0 - 2026-04-04

### Added

- Package-local and spec documentation now explain the package mental model,
  failure semantics, vector-store profiles, and freeze criteria in clearer
  human-facing language.

### Changed

- The package was realigned under the canonical `bijux-canon-index` identity,
  including namespace, application, interface, and orchestration surfaces.
- CLI workflows were split into clearer command groups for execution, ingest,
  query, validation, maintenance, and workspace tasks.
- API routes, request schemas, and orchestration helpers were decomposed into
  narrower modules for query, mutation, read, capability, and artifact
  workflows.
- Backend and orchestration support code was separated into smaller helpers for
  embedding preparation, ingest persistence, capability reporting, execution
  tracking, non-deterministic guard state, and artifact materialization.

### Fixed

- CLI help and freeze-spec coverage were restored after the package
  reorganization.
- Runtime state and generated artifacts were moved under the artifacts root so
  package trees stay cleaner during checks.

## 0.2.0 – 2026-02-03

### Added

- Explicit vector store adapters (memory/sqlite, FAISS, Qdrant) with capability reporting and status commands.
- Non-Deterministic (ND) execution model with budgets, quality metrics, witness options, and provenance audit fields.
- Embedding provider interface, cache controls, and embedding provenance metadata.
- Determinism fingerprints, replay gates, and conformance tests for stability.
- Benchmarks, dataset generator, and baseline regression checks.
- Human-first documentation, contracts, and operational guides (trust model, safety, failure modes).

### Changed

- CLI and API now require explicit vector store selection for persistence/ANN routes.
- Refusal semantics are standardized and surfaced consistently across CLI/API/provenance.
- Docs and onboarding flow rewritten for clarity, with explicit anti-goals and guarantees.

### Fixed

- Deterministic ordering rules and replay checks hardened across backends.
- Redaction rules tightened to prevent credential leakage in logs and provenance.

## 0.1.0 – first public release

### Added

- First public, contract-complete release of bijux-vex.
- Deterministic execution with replayable artifacts and provenance.
- Non-deterministic execution via ANN with approximation reports and randomness audit.
- CLI and FastAPI v1 surfaces frozen; OpenAPI schema versioned.
- Provenance, determinism, and execution ABI enforced via conformance tests.
