
# Changelog

All notable changes to `bijux-canon-reason` are documented here.

Historical release entries below preserve the wording that shipped with the
tagged release.

## 0.3.0 - 2026-04-05

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
- PyPI metadata, search keywords, and project URLs now make the canonical
  reasoning package easier to discover from package indexes and Bijux-owned
  docs.
- The package README now uses PyPI-safe badge and link targets, and it points
  legacy `bijux-rar` users to the canonical migration path and retired
  repository guidance.
- Package-local PyPI publication guidance is now checked in and shipped with
  the source distribution so reasoning release expectations stay attached to
  the package.
- Build-time version metadata now writes to a generated module so packaging
  commands stop dirtying the tracked source tree.
- Package-local ignore rules now cover Python package metadata directories so
  unpacked release artifacts stay cleaner during local validation.

### Fixed

- Fail-fast execution policy handling and root package gates were repaired after
  the refactor series.
- Fixture, benchmark-hygiene, and package-entrypoint regressions were cleaned up
  during the package reorganization.
- Release artifacts now ship the repository `LICENSE` file so downstream
  consumers receive the license text with the published package.
- API route modules now match the enforced Ruff formatting baseline so package
  lint checks stay reproducible in tox.

## v0.1.0 — Initial public release

- Evidence & citations: byte-span + sha256 verification, fail-closed grounding, replayable traces.
- Retrieval: chunked BM25 with pinned corpus/index provenance, deterministic rankings, replay guards.
- Reasoning: structured claims with enforced supports, insufficiency handling, baseline deterministic reasoner.
- Verification: strict invariant checks, negative-capability tests, invariant IDs wired to failures.
- API: SQLite-backed lifecycle, stateful Schemathesis coverage, auth + rate limiting + quotas.
- Tooling: make lint/test/quality/security/api gates, docs site, frozen contract scope `release_scope_v0_1_0.md`.
