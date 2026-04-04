# Changelog

All notable changes to `bijux-rar` are documented here.

This compatibility package exists to preserve the former reasoning
distribution name while the canonical package lives at `bijux-canon-reason`.

Historical release entries below preserve the wording that shipped with tagged
releases when a tagged changelog existed.

## Unreleased

- PyPI metadata now points legacy `bijux-rar` readers at the canonical
  `bijux-canon-reason` docs, migration guide, and Bijux-owned package family.
- The package README and overview now document the retired standalone
  repository, and the compatibility package now explicitly publishes the
  `bijux-rar` console script it documents.
- Package-local PyPI publication guidance is now checked in and shipped with
  the source distribution so legacy reasoning release expectations stay
  attached to the compatibility package.
- The published docs URL for `bijux-rar` now has its own migration landing
  page inside the shared handbook instead of sending legacy readers directly to
  canonical reasoning docs without context.

## 0.3.0 - 2026-04-04

### Added

- Package-local release history for the compatibility distribution so legacy
  installs have an auditable migration record of their own.

### Changed

- Compatibility messaging now consistently points new work to
  `bijux-canon-reason` while preserving the legacy distribution, import, and
  command names.

## v0.1.0 — Initial public release

- Evidence & citations: byte-span + sha256 verification, fail-closed grounding, replayable traces.
- Retrieval: chunked BM25 with pinned corpus/index provenance, deterministic rankings, replay guards.
- Reasoning: structured claims with enforced supports, insufficiency handling, baseline deterministic reasoner.
- Verification: strict invariant checks, negative-capability tests, invariant IDs wired to failures.
- API: SQLite-backed lifecycle, stateful Schemathesis coverage, auth + rate limiting + quotas.
- Tooling: make lint/test/quality/security/api gates, docs site, frozen contract scope `release_scope_v0_1_0.md`.
