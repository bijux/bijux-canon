# PyPI Publication Guide

Use this checklist when publishing the legacy `bijux-rar` compatibility
distribution from the monorepo.

## Release intent

Publish this package when the legacy `bijux-rar` distribution must keep
tracking `bijux-canon-reason` with the same install, import, and command
continuity guarantees.

## Pre-publish checks

- confirm the compatibility wheel still depends on `bijux-canon-reason` at the
  matching version
- confirm the `bijux-rar` command still resolves to the canonical reasoning CLI
  entrypoint
- confirm the README, overview, and changelog still explain the migration path
  away from the retired standalone repository

## Artifacts to review

- wheel and source distribution metadata
- legacy install instructions and migration links
- the preserved `bijux_rar` import surface and `bijux-rar` command

## Publish notes

- tag with the `bijux-canon-reason/v*` pattern because this compatibility
  package inherits the canonical reasoning version line
- publish only after compatibility messaging and the canonical migration links
  are aligned
