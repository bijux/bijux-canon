# PyPI Publication Guide

Use this checklist when publishing the legacy `bijux-agent` compatibility
distribution from the monorepo.

## Release intent

Publish this package when the legacy `bijux-agent` distribution must keep
tracking `bijux-canon-agent` with the same install, import, and command
continuity guarantees.

## Pre-publish checks

- confirm the compatibility wheel still depends on `bijux-canon-agent` at the
  matching version
- confirm the `bijux-agent` command still resolves to the canonical agent CLI
  entrypoint
- confirm the README, overview, and changelog still explain the migration path
  away from the retired standalone repository

## Artifacts to review

- wheel and source distribution metadata
- legacy install instructions and migration links
- the preserved `bijux_agent` import surface and `bijux-agent` command

## Publish notes

- tag with the `bijux-canon-agent/v*` pattern because this compatibility
  package inherits the canonical agent version line
- publish only after compatibility messaging and the canonical migration links
  are aligned
