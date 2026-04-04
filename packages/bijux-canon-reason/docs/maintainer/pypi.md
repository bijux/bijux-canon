# PyPI Publication Guide

Use this checklist when publishing `bijux-canon-reason` from the monorepo.

## Release intent

Publish this package when reasoning, verification, provenance, replay, or the
reasoning CLI and API contract changed in a way users need to install,
validate, or document independently.

## Pre-publish checks

- run `make PACKAGE=bijux-canon-reason lint`
- run `make PACKAGE=bijux-canon-reason quality`
- run `make PACKAGE=bijux-canon-reason test`
- confirm README links, package metadata, and migration notes still point to
  the canonical `bijux-canon-reason` package
- confirm the legacy `bijux-rar` compatibility path still matches the current
  package version and command story

## Artifacts to review

- wheel and source distribution metadata
- CLI help for `bijux-canon-reason`
- API schemas and any replay or provenance artifacts with public consumers
- docs that describe verification, reasoning behavior, and evidence contracts

## Publish notes

- tag with the `bijux-canon-reason/v*` pattern so Hatch VCS resolves the
  package version correctly
- keep `README.md`, `CHANGELOG.md`, and package metadata aligned before upload
- if public verification or provenance contracts changed, update the canonical
  docs before publishing artifacts
