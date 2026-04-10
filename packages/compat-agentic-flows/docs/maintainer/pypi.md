# PyPI Publication Guide

Use this checklist when publishing the legacy `agentic-flows` compatibility
distribution from the monorepo.

## Release Surface

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/agentic-flows/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![Verify](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml)
[![Publish](https://github.com/bijux/bijux-canon/actions/workflows/publish.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/publish.yml)
[![Docs](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml)

- legacy package handbook: <https://bijux.io/bijux-canon/compat-packages/catalog/agentic-flows/>
- canonical package docs: <https://bijux.io/bijux-canon/bijux-canon-runtime/>
- migration guide: <https://bijux.io/bijux-canon/compat-packages/migration/migration-guidance/>
- package directory: <https://github.com/bijux/bijux-canon/tree/main/packages/compat-agentic-flows>
- verify workflow: <https://github.com/bijux/bijux-canon/actions/workflows/verify.yml>
- publish workflow: <https://github.com/bijux/bijux-canon/actions/workflows/publish.yml>
- docs workflow: <https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml>

## Release intent

Publish this package when the legacy distribution must keep tracking the
canonical `bijux-canon-runtime` version with the same install, import, and
command continuity guarantees.

The published package docs URL for this legacy name is
<https://bijux.io/bijux-canon/compat-packages/catalog/agentic-flows/> so PyPI readers
land on migration-specific guidance before moving to the canonical runtime
handbook.

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

- tag the repository with the shared `v*` release pattern because this
  compatibility package now resolves the same version as the canonical family
- publish only after compatibility messaging and the canonical migration links
  are aligned
