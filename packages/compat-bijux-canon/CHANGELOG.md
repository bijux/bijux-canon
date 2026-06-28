# Changelog

All notable changes to `bijux-canon` are documented here.

This compatibility package exists to preserve the shorter family-root runtime
distribution name while the canonical package lives at `bijux-canon-runtime`.

Historical release entries below preserve the wording that shipped with tagged
releases when a tagged changelog existed. Releases that shipped without a
changelog update are reconstructed from tag annotations and release diffs.

## 0.3.8 - 2026-06-28

### Added

- Published `bijux-canon` as a real compatibility alias distribution for
  `bijux-canon-runtime`, including the `bijux_canon` import root and the
  `bijux-canon` CLI command.

### Changed

- Documented the shorter family-root alias contract so package metadata, README
  guidance, and handbook links point readers back to `bijux-canon-runtime`.

### Fixed

- The compatibility package now resolves imports and submodules to the same
  canonical runtime modules instead of behaving like a migration-only stub.
- Release fallback metadata now aligns with the synchronized `0.3.8` canon
  release line.
