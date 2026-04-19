# PyPI Publication Guide

Use this checklist when publishing `bijux-canon-agent` from the monorepo.

## Release Surface

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/05-bijux-canon-agent/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![Verify](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml)
[![Publish](https://github.com/bijux/bijux-canon/actions/workflows/release-github.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/release-github.yml)
[![Docs](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml)

- package guide: <https://bijux.io/bijux-canon/05-bijux-canon-agent/>
- release and versioning: <https://bijux.io/bijux-canon/05-bijux-canon-agent/operations/release-and-versioning/>
- package directory: <https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-agent>
- verify workflow: <https://github.com/bijux/bijux-canon/actions/workflows/verify.yml>
- publish workflow: <https://github.com/bijux/bijux-canon/actions/workflows/release-github.yml>
- docs workflow: <https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml>

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
- confirm the compatibility guidance still points previous `bijux-agent` users to
  the right migration path

## Artifacts to review

- wheel and source distribution metadata
- CLI help for `bijux-canon-agent`
- package-local docs and migration references
- any public API or trace contract changes that downstream users would observe

## Publish notes

- tag the repository with the shared `v*` release pattern so every package,
  including `bijux-canon-agent`, resolves the same version
- publish only after the package changelog explains the user-visible change
- if a release changes a public boundary, update the canonical docs before
  uploading artifacts
