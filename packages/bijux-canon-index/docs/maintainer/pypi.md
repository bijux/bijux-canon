# PyPI Publication Guide

Use this checklist when publishing `bijux-canon-index` from the monorepo.

## Release Surface

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon-index/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![Verify](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml)
[![Publish](https://github.com/bijux/bijux-canon/actions/workflows/publish.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/publish.yml)
[![Docs](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml)

- package guide: <https://bijux.io/bijux-canon/bijux-canon-index/>
- release and versioning: <https://bijux.io/bijux-canon/bijux-canon-index/operations/release-and-versioning/>
- package directory: <https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-index>
- verify workflow: <https://github.com/bijux/bijux-canon/actions/workflows/verify.yml>
- publish workflow: <https://github.com/bijux/bijux-canon/actions/workflows/publish.yml>
- docs workflow: <https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml>

## Release intent

Publish this package when indexing, vector execution, replayable ANN behavior,
or the index CLI and API contract changed in a way users need to install or
document independently.

## Pre-publish checks

- run `make PACKAGE=bijux-canon-index lint`
- run `make PACKAGE=bijux-canon-index quality`
- run `make PACKAGE=bijux-canon-index test`
- confirm README links, package metadata, and migration notes still point to
  the canonical `bijux-canon-index` package
- confirm the legacy `bijux-vex` compatibility path still matches the current
  package version and command story

## Artifacts to review

- wheel and source distribution metadata
- CLI help for `bijux-canon-index`
- API schema outputs, freeze artifacts, and schema hashes
- docs that describe vector backends, replay boundaries, and operator workflows

## Publish notes

- tag the repository with the shared `v*` release pattern so every package,
  including `bijux-canon-index`, resolves the same version
- keep `README.md`, `CHANGELOG.md`, and package metadata aligned before upload
- if public API, replay, or vector-store contracts changed, update the
  canonical docs before publishing artifacts
