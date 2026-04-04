# PyPI Publication Guide

Use this checklist when publishing `bijux-canon-index` from the monorepo.

## Release intent

Publish this package when indexing, vector execution, replayable ANN behavior,
or the index CLI and API contract changed in a way users need to install or
document independently.

## Pre-publish checks

- run `make PACKAGE=bijux-canon-index lint`
- run `make PACKAGE=bijux-canon-index quality`
- run `make PACKAGE=bijux-canon-index test`
- confirm README links, package metadata, and migration notes still point to
  the canonical `bijux-canon-index` package
- confirm the legacy `bijux-vex` compatibility path still matches the current
  package version and command story

## Artifacts to review

- wheel and source distribution metadata
- CLI help for `bijux-canon-index`
- API schema outputs, freeze artifacts, and schema hashes
- docs that describe vector backends, replay boundaries, and operator workflows

## Publish notes

- tag with the `bijux-canon-index/v*` pattern so Hatch VCS resolves the
  package version correctly
- keep `README.md`, `CHANGELOG.md`, and package metadata aligned before upload
- if public API, replay, or vector-store contracts changed, update the
  canonical docs before publishing artifacts
