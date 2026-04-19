# PyPI Publication Guide

Use this checklist when publishing `bijux-canon-ingest` from the monorepo.

## Release Surface

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon-ingest/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![Verify](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml)
[![Publish](https://github.com/bijux/bijux-canon/actions/workflows/release-github.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/release-github.yml)
[![Docs](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml)

- package guide: <https://bijux.io/bijux-canon/bijux-canon-ingest/>
- release and versioning: <https://bijux.io/bijux-canon/bijux-canon-ingest/operations/release-and-versioning/>
- package directory: <https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-ingest>
- verify workflow: <https://github.com/bijux/bijux-canon/actions/workflows/verify.yml>
- publish workflow: <https://github.com/bijux/bijux-canon/actions/workflows/release-github.yml>
- docs workflow: <https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml>

## Release intent

Publish this package when document ingestion, chunking, retrieval preparation,
or the ingest CLI and API contract changed in a way users need to install or
document independently.

## Pre-publish checks

- run `make PACKAGE=bijux-canon-ingest lint`
- run `make PACKAGE=bijux-canon-ingest quality`
- run `make PACKAGE=bijux-canon-ingest test`
- confirm README links, package metadata, and migration notes still point to
  the canonical `bijux-canon-ingest` distribution
- confirm the legacy `bijux-rag` compatibility path still matches the current
  package version and command story

## Artifacts to review

- wheel and source distribution metadata
- CLI help for `bijux-canon-ingest`
- API schemas and any ingest contract fixtures
- docs that describe chunking, retrieval preparation, and operator workflows

## Publish notes

- tag the repository with the shared `v*` release pattern so every package,
  including `bijux-canon-ingest`, resolves the same version
- keep `README.md`, `CHANGELOG.md`, and package metadata aligned before upload
- if public ingest or retrieval contracts changed, update the canonical docs
  before publishing artifacts
