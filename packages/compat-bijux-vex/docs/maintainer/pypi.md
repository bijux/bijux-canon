# PyPI Publication Guide

Use this checklist when publishing the legacy `bijux-vex` compatibility
distribution from the monorepo.

## Release intent

Publish this package when the legacy `bijux-vex` distribution must keep
tracking `bijux-canon-index` with the same install, import, and command
continuity guarantees.

## Pre-publish checks

- confirm the compatibility wheel still depends on `bijux-canon-index` at the
  matching version
- confirm the `bijux-vex` command still resolves to the canonical index CLI
  entrypoint
- confirm the README, overview, and changelog still explain the migration path
  away from the retired standalone repository

## Artifacts to review

- wheel and source distribution metadata
- legacy install instructions and migration links
- the preserved `bijux_vex` import surface and `bijux-vex` command

## Publish notes

- tag with the `bijux-canon-index/v*` pattern because this compatibility
  package inherits the canonical index version line
- publish only after compatibility messaging and the canonical migration links
  are aligned
