# Changelog

All notable changes to Bijux Vex are documented here. This project adheres to Semantic Versioning and the Keep a Changelog format.

## Unreleased

### Added

- (add new entries via Towncrier fragments in `changelog.d/`)

### Changed

- (add here)

### Fixed

- (add here)

## 0.2.0 – 2026-02-03

### Added

- Explicit vector store adapters (memory/sqlite, FAISS, Qdrant) with capability reporting and status commands.
- Non‑Deterministic (ND) execution model with budgets, quality metrics, witness options, and provenance audit fields.
- Embedding provider interface, cache controls, and embedding provenance metadata.
- Determinism fingerprints, replay gates, and conformance tests for stability.
- Benchmarks, dataset generator, and baseline regression checks.
- Human‑first documentation, contracts, and operational guides (trust model, safety, failure modes).

### Changed

- CLI and API now require explicit vector store selection for persistence/ANN routes.
- Refusal semantics are standardized and surfaced consistently across CLI/API/provenance.
- Docs and onboarding flow rewritten for clarity, with explicit anti‑goals and guarantees.

### Fixed

- Deterministic ordering rules and replay checks hardened across backends.
- Redaction rules tightened to prevent credential leakage in logs and provenance.

## 0.1.0 – first public release

### Added

- First public, contract‑complete release of bijux‑vex.
- Deterministic execution with replayable artifacts and provenance.
- Non‑deterministic execution via ANN with approximation reports and randomness audit.
- CLI and FastAPI v1 surfaces frozen; OpenAPI schema versioned.
- Provenance, determinism, and execution ABI enforced via conformance tests.
