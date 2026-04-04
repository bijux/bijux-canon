# PyPI Publication Guide

Use this checklist when publishing the legacy `agentic-flows` compatibility
distribution from the monorepo.

## Release intent

Publish this package when the legacy distribution must keep tracking the
canonical `bijux-canon-runtime` version with the same install, import, and
command continuity guarantees.

## Pre-publish checks

- confirm the compatibility wheel still depends on `bijux-canon-runtime` at
  the matching version
- confirm the `agentic-flows` command still resolves to the canonical runtime
  CLI entrypoint
- confirm the README, overview, and changelog still explain the migration path
  away from the retired standalone repository

## Artifacts to review

- wheel and source distribution metadata
- legacy install instructions and migration links
- the preserved `agentic_flows` import surface and `agentic-flows` command

## Publish notes

- tag with the `bijux-canon-runtime/v*` pattern because this compatibility
  package inherits the canonical runtime version line
- publish only after compatibility messaging and the canonical migration links
  are aligned
