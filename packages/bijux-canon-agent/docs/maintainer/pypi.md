# PyPI Publication Guide

Use this checklist when publishing `bijux-canon-agent` from the monorepo.

## Release intent

Publish this package when the canonical agent surface changed in a way that
users need to install, test, or document independently of the rest of the
family.

## Pre-publish checks

- run `make PACKAGE=bijux-canon-agent lint`
- run `make PACKAGE=bijux-canon-agent quality`
- run `make PACKAGE=bijux-canon-agent test`
- confirm `README.md`, `CHANGELOG.md`, and package metadata still describe the
  canonical `bijux-canon-agent` distribution
- confirm the compatibility guidance still points legacy `bijux-agent` users to
  the right migration path

## Artifacts to review

- wheel and source distribution metadata
- CLI help for `bijux-canon-agent`
- package-local docs and migration references
- any public API or trace contract changes that downstream users would observe

## Publish notes

- tag with the `bijux-canon-agent/v*` pattern so Hatch VCS resolves the
  package version correctly
- publish only after the package changelog explains the user-visible change
- if a release changes a public boundary, update the canonical docs before
  uploading artifacts
