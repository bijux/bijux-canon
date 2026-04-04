
# Changelog

All notable changes to `bijux-canon-reason` are documented here.

Historical release entries below preserve the wording that shipped with the
tagged release.

## Unreleased

- No package-local changes recorded yet.

## 0.3.0 - 2026-04-04

### Added

- Package-local documentation now explains reasoning-package ownership,
  architecture, boundaries, contracts, and test strategy in clearer human-facing
  language.

### Changed

- The package was realigned under the canonical `bijux-canon-reason` identity,
  with planning, execution, retrieval, reasoning, trace, and verification code
  promoted into clearer top-level package areas.
- Runtime and API code were decomposed into smaller units for step execution,
  tool dispatch, provenance handling, evaluation summaries, replay
  orchestration, and invariant validation.
- Package entrypoints and storage helpers were simplified so reasoning flows are
  easier to follow and internal dependencies are less tangled.

### Fixed

- Fail-fast execution policy handling and root package gates were repaired after
  the refactor series.
- Fixture, benchmark-hygiene, and package-entrypoint regressions were cleaned up
  during the package reorganization.

## v0.1.0 — Initial public release

- Evidence & citations: byte-span + sha256 verification, fail-closed grounding, replayable traces.
- Retrieval: chunked BM25 with pinned corpus/index provenance, deterministic rankings, replay guards.
- Reasoning: structured claims with enforced supports, insufficiency handling, baseline deterministic reasoner.
- Verification: strict invariant checks, negative-capability tests, invariant IDs wired to failures.
- API: SQLite-backed lifecycle, stateful Schemathesis coverage, auth + rate limiting + quotas.
- Tooling: make lint/test/quality/security/api gates, docs site, frozen contract scope `release_scope_v0_1_0.md`.
