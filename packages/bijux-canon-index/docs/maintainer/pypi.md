# PyPI Publication Guide

Use this checklist when publishing `bijux-canon-index` from the monorepo.

## Package Family Badges

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon-runtime/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![CI: runtime](https://github.com/bijux/bijux-canon/actions/workflows/ci-bijux-canon-runtime.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/ci-bijux-canon-runtime.yml)
[![CI: agent](https://github.com/bijux/bijux-canon/actions/workflows/ci-bijux-canon-agent.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/ci-bijux-canon-agent.yml)
[![CI: ingest](https://github.com/bijux/bijux-canon/actions/workflows/ci-bijux-canon-ingest.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/ci-bijux-canon-ingest.yml)
[![CI: reason](https://github.com/bijux/bijux-canon/actions/workflows/ci-bijux-canon-reason.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/ci-bijux-canon-reason.yml)
[![CI: index](https://github.com/bijux/bijux-canon/actions/workflows/ci-bijux-canon-index.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/ci-bijux-canon-index.yml)

[![bijux-canon-runtime](https://img.shields.io/pypi/v/bijux-canon-runtime?label=runtime&logo=pypi)](https://pypi.org/project/bijux-canon-runtime/)
[![bijux-canon-agent](https://img.shields.io/pypi/v/bijux-canon-agent?label=agent&logo=pypi)](https://pypi.org/project/bijux-canon-agent/)
[![bijux-canon-ingest](https://img.shields.io/pypi/v/bijux-canon-ingest?label=ingest&logo=pypi)](https://pypi.org/project/bijux-canon-ingest/)
[![bijux-canon-reason](https://img.shields.io/pypi/v/bijux-canon-reason?label=reason&logo=pypi)](https://pypi.org/project/bijux-canon-reason/)
[![bijux-canon-index](https://img.shields.io/pypi/v/bijux-canon-index?label=index&logo=pypi)](https://pypi.org/project/bijux-canon-index/)

[![agentic-flows](https://img.shields.io/pypi/v/agentic-flows?label=agentic--flows&logo=pypi)](https://pypi.org/project/agentic-flows/)
[![bijux-agent](https://img.shields.io/pypi/v/bijux-agent?label=bijux--agent&logo=pypi)](https://pypi.org/project/bijux-agent/)
[![bijux-rag](https://img.shields.io/pypi/v/bijux-rag?label=bijux--rag&logo=pypi)](https://pypi.org/project/bijux-rag/)
[![bijux-rar](https://img.shields.io/pypi/v/bijux-rar?label=bijux--rar&logo=pypi)](https://pypi.org/project/bijux-rar/)
[![bijux-vex](https://img.shields.io/pypi/v/bijux-vex?label=bijux--vex&logo=pypi)](https://pypi.org/project/bijux-vex/)

[![Runtime docs](https://img.shields.io/badge/docs-runtime-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-runtime/)
[![Agent docs](https://img.shields.io/badge/docs-agent-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-agent/)
[![Ingest docs](https://img.shields.io/badge/docs-ingest-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-ingest/)
[![Reason docs](https://img.shields.io/badge/docs-reason-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-reason/)
[![Index docs](https://img.shields.io/badge/docs-index-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-index/)

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
