# PyPI Publication Guide

Use this checklist when publishing the legacy `bijux-vex` compatibility
distribution from the monorepo.

## Release Surface

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-vex/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![Verify](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml)
[![Publish](https://github.com/bijux/bijux-canon/actions/workflows/release-github.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/release-github.yml)
[![Docs](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml)

- legacy package handbook: <https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-vex/>
- canonical package docs: <https://bijux.io/bijux-canon/bijux-canon-index/>
- migration guide: <https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/>
- package directory: <https://github.com/bijux/bijux-canon/tree/main/packages/compat-bijux-vex>
- verify workflow: <https://github.com/bijux/bijux-canon/actions/workflows/verify.yml>
- publish workflow: <https://github.com/bijux/bijux-canon/actions/workflows/release-github.yml>
- docs workflow: <https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml>

## Release intent

Publish this package when the legacy `bijux-vex` distribution must keep
tracking `bijux-canon-index` with the same install, import, and command
continuity guarantees.

The published package docs URL for this legacy name is
<https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-vex/> so PyPI readers land
on migration-specific guidance before moving to the canonical index handbook.

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

- tag the repository with the shared `v*` release pattern because this
  compatibility package now resolves the same version as the canonical family
- publish only after compatibility messaging and the canonical migration links
  are aligned
