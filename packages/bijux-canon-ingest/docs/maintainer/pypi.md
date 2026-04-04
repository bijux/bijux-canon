# PyPI Publication Guide

Use this checklist when publishing `bijux-canon-ingest` from the monorepo.

## Release intent

Publish this package when document ingestion, chunking, retrieval preparation,
or the ingest CLI and API contract changed in a way users need to install or
document independently.

## Pre-publish checks

- run `make PACKAGE=bijux-canon-ingest lint`
- run `make PACKAGE=bijux-canon-ingest quality`
- run `make PACKAGE=bijux-canon-ingest test`
- confirm README links, package metadata, and migration notes still point to
  the canonical `bijux-canon-ingest` distribution
- confirm the legacy `bijux-rag` compatibility path still matches the current
  package version and command story

## Artifacts to review

- wheel and source distribution metadata
- CLI help for `bijux-canon-ingest`
- API schemas and any ingest contract fixtures
- docs that describe chunking, retrieval preparation, and operator workflows

## Publish notes

- tag with the `bijux-canon-ingest/v*` pattern so Hatch VCS resolves the
  package version correctly
- keep `README.md`, `CHANGELOG.md`, and package metadata aligned before upload
- if public ingest or retrieval contracts changed, update the canonical docs
  before publishing artifacts
