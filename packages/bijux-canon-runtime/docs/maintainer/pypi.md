# PyPI Publication Guide

Use this checklist when publishing `bijux-canon-runtime` from the monorepo.

## Release Surface

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon-runtime/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![Verify](https://github.com/bijux/bijux-canon/workflows/repo%20/%20verify/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml)
[![Publish](https://github.com/bijux/bijux-canon/workflows/release-github/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/release-github.yml)
[![Docs](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml)

- package guide: <https://bijux.io/bijux-canon/bijux-canon-runtime/>
- release and versioning: <https://bijux.io/bijux-canon/bijux-canon-runtime/operations/release-and-versioning/>
- package directory: <https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-runtime>
- verify workflow: <https://github.com/bijux/bijux-canon/actions/workflows/verify.yml>
- publish workflow: <https://github.com/bijux/bijux-canon/actions/workflows/release-github.yml>
- docs workflow: <https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml>

## Release intent

Publish this package when runtime execution, replay policy, persistence, or the
operator-facing contract changed in a way that users need to consume as a
versioned distribution.

## Pre-publish checks

- run `make PACKAGE=bijux-canon-runtime lint`
- run `make PACKAGE=bijux-canon-runtime quality`
- run `make PACKAGE=bijux-canon-runtime test`
- confirm runtime metadata, README links, and migration notes still point to
  the canonical `bijux-canon-runtime` package
- confirm the compatibility path for `agentic-flows` still matches the current
  release story

## Artifacts to review

- wheel and source distribution metadata
- CLI help for `bijux-canon-runtime`
- API schema outputs and schema-hash artifacts
- replay and persistence docs that operators use during incidents or upgrades

## Publish notes

- tag the repository with the shared `v*` release pattern so every package,
  including `bijux-canon-runtime`, resolves the same version
- publish only after changelog entries, runtime docs, and package metadata are
  aligned
- if execution or replay contracts changed, verify the canonical docs before
  uploading artifacts
