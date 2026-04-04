# PyPI Publication Guide

Use this checklist when publishing the legacy `bijux-rag` compatibility
distribution from the monorepo.

## Release intent

Publish this package when the legacy `bijux-rag` distribution must keep
tracking `bijux-canon-ingest` with the same install, import, and command
continuity guarantees.

## Pre-publish checks

- confirm the compatibility wheel still depends on `bijux-canon-ingest` at the
  matching version
- confirm the `bijux-rag` command still resolves to the canonical ingest CLI
  entrypoint
- confirm the README, overview, and changelog still explain the migration path
  away from the retired standalone repository

## Artifacts to review

- wheel and source distribution metadata
- legacy install instructions and migration links
- the preserved `bijux_rag` import surface and `bijux-rag` command

## Publish notes

- tag with the `bijux-canon-ingest/v*` pattern because this compatibility
  package inherits the canonical ingest version line
- publish only after compatibility messaging and the canonical migration links
  are aligned
