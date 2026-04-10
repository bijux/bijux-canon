# Changelog

All notable changes to `bijux-vex` are documented here.

This compatibility package exists to preserve the former index distribution
name while the canonical package lives at `bijux-canon-index`.

Historical release entries below preserve the wording that shipped with tagged
releases when a tagged changelog existed. Releases that shipped without a
changelog update are reconstructed from tag annotations and release diffs.

## 0.3.2 - 2026-04-10

### Fixed

- Compatibility package fallback metadata now aligns with the synchronized
  `v0.3.2` canon release.

## 0.3.0 - 2026-04-05

### Added

- Package-local release history for the compatibility distribution so legacy
  installs have a durable migration record instead of relying only on canonical
  package notes.

### Changed

- Compatibility messaging now consistently points new work to
  `bijux-canon-index` while preserving the legacy distribution, import, and
  command names.
- PyPI metadata now points legacy `bijux-vex` readers at the canonical
  `bijux-canon-index` docs, migration guide, and Bijux-owned package family.
- The package README and overview now document the retired standalone
  repository and use PyPI-safe badge and link targets.
- Package-local PyPI publication guidance is now checked in and shipped with
  the source distribution so legacy index release expectations stay attached to
  the compatibility package.
- The published docs URL for `bijux-vex` now has its own migration landing
  page inside the shared handbook instead of sending legacy readers directly to
  canonical index docs without context.

### Fixed

- Release artifacts now ship the repository license and publish package-local
  ignore rules instead of leaking repo-wide ignore policy into the source
  distribution.

## 0.2.2 - 2026-02-04

### Fixed

- README inclusion in the source distribution was restored for PyPI builds.

## 0.2.1 - 2026-02-04

### Fixed

- Docs dependency installation and security-audit scope were corrected for the
  patch release.

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

## v0.1.0 (first public release)

- First public, contract-complete release of bijux-vex.
- Deterministic execution with replayable artifacts and provenance.
- Non-deterministic execution via ANN with approximation reports and randomness audit.
- CLI and FastAPI v1 surfaces frozen; OpenAPI schema versioned.
- Provenance, determinism, and execution ABI enforced via conformance tests.
