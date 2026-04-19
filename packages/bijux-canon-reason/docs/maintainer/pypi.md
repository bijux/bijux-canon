# PyPI Publication Guide

Use this checklist when publishing `bijux-canon-reason` from the monorepo.

## Release Surface

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon-reason/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![Verify](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml)
[![Publish](https://github.com/bijux/bijux-canon/actions/workflows/release-github.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/release-github.yml)
[![Docs](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml)

- package guide: <https://bijux.io/bijux-canon/bijux-canon-reason/>
- release and versioning: <https://bijux.io/bijux-canon/bijux-canon-reason/operations/release-and-versioning/>
- package directory: <https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-reason>
- verify workflow: <https://github.com/bijux/bijux-canon/actions/workflows/verify.yml>
- publish workflow: <https://github.com/bijux/bijux-canon/actions/workflows/release-github.yml>
- docs workflow: <https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml>

## Release intent

Publish this package when reasoning, verification, provenance, replay, or the
reasoning CLI and API contract changed in a way users need to install,
validate, or document independently.

## Pre-publish checks

- run `make PACKAGE=bijux-canon-reason lint`
- run `make PACKAGE=bijux-canon-reason quality`
- run `make PACKAGE=bijux-canon-reason test`
- confirm README links, package metadata, and migration notes still point to
  the canonical `bijux-canon-reason` package
- confirm the legacy `bijux-rar` compatibility path still matches the current
  package version and command story

## Artifacts to review

- wheel and source distribution metadata
- CLI help for `bijux-canon-reason`
- API schemas and any replay or provenance artifacts with public consumers
- docs that describe verification, reasoning behavior, and evidence contracts

## Publish notes

- tag the repository with the shared `v*` release pattern so every package,
  including `bijux-canon-reason`, resolves the same version
- keep `README.md`, `CHANGELOG.md`, and package metadata aligned before upload
- if public verification or provenance contracts changed, update the canonical
  docs before publishing artifacts
