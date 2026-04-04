# PyPI Publication Guide

Use this checklist when publishing `bijux-canon-runtime` from the monorepo.

## Release intent

Publish this package when runtime execution, replay policy, persistence, or the
operator-facing contract changed in a way that users need to consume as a
versioned distribution.

## Pre-publish checks

- run `make PACKAGE=bijux-canon-runtime lint`
- run `make PACKAGE=bijux-canon-runtime quality`
- run `make PACKAGE=bijux-canon-runtime test`
- confirm runtime metadata, README links, and migration notes still point to
  the canonical `bijux-canon-runtime` package
- confirm the compatibility path for `agentic-flows` still matches the current
  release story

## Artifacts to review

- wheel and source distribution metadata
- CLI help for `bijux-canon-runtime`
- API schema outputs and schema-hash artifacts
- replay and persistence docs that operators use during incidents or upgrades

## Publish notes

- tag with the `bijux-canon-runtime/v*` pattern so Hatch VCS resolves the
  package version correctly
- publish only after changelog entries, runtime docs, and package metadata are
  aligned
- if execution or replay contracts changed, verify the canonical docs before
  uploading artifacts
