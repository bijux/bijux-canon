---
title: gh-workflows
audience: mixed
type: index
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# gh-workflows

Open this section to understand the GitHub Actions entrypoints and reusable
building blocks that verify, release, and document the repository.

The top-level entrypoints are `verify.yml` for pushes and pull requests,
`deploy-docs.yml` for handbook publication from `main`, and the release split
workflows (`release-github.yml`, `release-pypi.yml`, `release-ghcr.yml`) for
tag-driven publication. `ci.yml` and `release-artifacts.yml` are reusable
workflows called by those entrypoints rather than standalone manual surfaces.

## Pages In gh-workflows

- [verify](https://bijux.io/bijux-canon/07-bijux-canon-maintain/gh-workflows/verify/)
- [reusable-workflows](https://bijux.io/bijux-canon/07-bijux-canon-maintain/gh-workflows/reusable-workflows/)
- [deploy-docs](https://bijux.io/bijux-canon/07-bijux-canon-maintain/gh-workflows/deploy-docs/)
- [release-workflows](https://bijux.io/bijux-canon/07-bijux-canon-maintain/gh-workflows/release-workflows/)

## Open gh-workflows When

- the concern is about workflow triggers, job trees, or reusable workflow
  composition
- you need to know which GitHub Actions file owns verification, docs
  publication, or release automation
- the answer should come from checked-in workflow contracts rather than CI
  folklore

## Open Another Section When

- the question is about Make target routing rather than GitHub Actions
- the issue belongs to one product package contract instead of repository
  automation
- you only need maintainer helper code rather than workflow entrypoints

## Start Here

- open [verify](https://bijux.io/bijux-canon/07-bijux-canon-maintain/gh-workflows/verify/) when the concern starts from pull request or push
  verification
- open [deploy-docs](https://bijux.io/bijux-canon/07-bijux-canon-maintain/gh-workflows/deploy-docs/) when the concern is docs publication from
  `main`
- open [release-workflows](https://bijux.io/bijux-canon/07-bijux-canon-maintain/gh-workflows/release-workflows/) when the concern is tag-driven
  publication
- open [reusable-workflows](https://bijux.io/bijux-canon/07-bijux-canon-maintain/gh-workflows/reusable-workflows/) when the key question is job
  reuse or nested workflow composition

## Concrete Anchors

- `.github/workflows/verify.yml` for verification entry logic
- `.github/workflows/deploy-docs.yml` for published handbook deployment
- `.github/workflows/release-github.yml`, `.github/workflows/release-pypi.yml`, and `.github/workflows/release-ghcr.yml` for release entrypoints
- `.github/workflows/ci.yml` and `.github/workflows/release-artifacts.yml` for reusable execution trees

## Workflow Standard

Workflow ownership should be discoverable from the checked-in YAML files and
their call graph. If a maintainer still has to infer the release or verify path
from past Actions runs, the workflow surface is under-documented.
