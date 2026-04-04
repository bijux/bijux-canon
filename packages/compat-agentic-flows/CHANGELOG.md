# Changelog

All notable changes to `agentic-flows` are documented here.

This compatibility package exists to preserve the former runtime distribution
name while the canonical package lives at `bijux-canon-runtime`.

Historical release entries below preserve the wording that shipped with tagged
releases when a tagged changelog existed. Releases that shipped without a
changelog update are reconstructed from tag annotations and release diffs.

## Unreleased

- PyPI metadata now points legacy `agentic-flows` readers at the canonical
  `bijux-canon-runtime` docs, migration guide, and Bijux-owned package family.
- The package README and overview now document the retired standalone
  repository and use PyPI-safe badge and link targets.
- Package-local PyPI publication guidance is now checked in and shipped with
  the source distribution so legacy runtime release expectations stay attached
  to the compatibility package.

## 0.3.0 - 2026-04-04

### Added

- Package-local release history for the compatibility distribution so migration
  releases are traceable without reading only canonical package notes.

### Changed

- Compatibility messaging now consistently points new work to
  `bijux-canon-runtime` while preserving the legacy distribution, import, and
  command names.

## 0.1.1 - 2026-01-21

### Changed

- Public release automation and CI coverage were tightened without changing the
  runtime compatibility surface.

## 0.1.0 – 2025-01-21

### Added

- **Core runtime**
  - Deterministic execution lifecycle with planning, execution, and finalization phases.
  - Execution modes: plan, dry-run, live, observe, and unsafe.
  - Strict determinism guardrails with explicit seed and environment fingerprints.
- **Non-determinism governance**
  - Declared non-determinism intent model and policy validation.
  - Entropy budgeting with enforcement, exhaustion semantics, and replay analysis.
  - Determinism profiles with structured replay metadata.
- **Replay and audit**
  - Replay modes (strict/bounded/observational) and acceptability classifications.
  - Trace diffing, replay envelopes, and deterministic replay validation.
  - Observability capture for events, artifacts, evidence, and entropy usage.
- **Persistence**
  - DuckDB execution store with schema contract enforcement and migrations.
  - Execution schema, replay envelopes, checkpoints, and trace storage.
- **CLI + API surface**
  - CLI commands for planning, running, replaying, inspecting, and diffing runs.
  - OpenAPI schema for the HTTP surface with schema hash stability checks.
- **Policies and verification**
  - Verification policy and arbitration plumbing for reasoning and evidence checks.
  - Failure taxonomy with deterministic error classes.
- **Docs and examples**
  - Determinism/non-determinism contract docs and storage model guidance.
  - Examples for deterministic and replay behavior.
- **Quality gates**
  - Makefile orchestration for tests, linting, docs, API checks, SBOM, and citation outputs.
