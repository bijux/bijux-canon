# Changelog

All notable changes to `bijux-canon-index` are documented here.

Historical release entries below preserve the wording that shipped with the
tagged release, including legacy distribution naming where applicable.

## 0.3.6 - 2026-04-20

### Changed

- Prepared the `v0.3.6` release line by aligning fallback versions and inter-package dependency floors across the repository.
- Synchronized release automation and governance with the `bijux-std v0.1.3` shared standards baseline.

### Fixed

- `release-pypi.yml` now uses parse-safe publication gating for token/bootstrap checks.
- Protected workflow policy checks now accept shared-manifest-driven standards updates through approved control paths.

## 0.3.5 - 2026-04-19

### Changed

- Package contract docs and compatibility tests now reference canonical API
  schema paths under `apis/bijux-canon-index/v1`.
- Handbook and package documentation links now resolve canonical package
  handbooks without stale numbered package slugs.

## 0.3.4 - 2026-04-11

### Fixed

- Release fallback metadata and source-checkout version fallback now align with
  the synchronized `v0.3.4` tag.
- Package README badge links now follow the shared badge catalog and point to
  the exact GHCR package pages used for published index bundles.

## 0.3.2 - 2026-04-10

### Fixed

- Release fallback metadata and source-checkout version fallback now align with
  the `v0.3.2` tag.

## 0.3.0 - 2026-04-05

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
- PyPI metadata, search keywords, and project URLs now make the canonical
  index package easier to discover from package indexes and Bijux-owned docs.
- The package README now uses PyPI-safe badge and link targets, and it points
  legacy `bijux-vex` users to the canonical migration path and retired
  repository guidance.
- Package-local PyPI publication guidance is now checked in and shipped with
  the source distribution so index release expectations stay attached to the
  package.
- Build-time version metadata now writes to a generated module so packaging
  commands stop dirtying the tracked source tree.
- Package-local ignore rules now cover Python package metadata directories so
  unpacked release artifacts stay cleaner during local validation.
- OpenAPI freeze artifacts and release-gate expectations were refreshed to
  match the current FastAPI-generated validation schema and 422 response
  wording.

### Fixed

- CLI help and freeze-spec coverage were restored after the package
  reorganization.
- Runtime state and generated artifacts were moved under the artifacts root so
  package trees stay cleaner during checks.
- Source distributions now include the full `src/bijux_canon_index` tree
  instead of publishing only the typed marker file.
- Release artifacts now ship the repository `LICENSE` file so downstream
  consumers receive the license text with the published package.
- The checked-in YAML and JSON OpenAPI artifacts are back in sync so
  repository-level API contract checks validate the same v1 surface.
- The checked-in v1 schema now includes the current FastAPI validation error
  shape so API drift checks match the live application contract.

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

- First public, contract-complete release of bijux-vex.
- Deterministic execution with replayable artifacts and provenance.
- Non-deterministic execution via ANN with approximation reports and randomness audit.
- CLI and FastAPI v1 surfaces frozen; OpenAPI schema versioned.
- Provenance, determinism, and execution ABI enforced via conformance tests.
