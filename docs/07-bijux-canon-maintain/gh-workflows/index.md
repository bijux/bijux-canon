---
title: gh-workflows
audience: mixed
type: index
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-19
---

# gh-workflows

The workflow section explains the GitHub Actions entrypoints and reusable
building blocks that verify, release, and document the repository.

Use these pages when you need to know which workflow starts on push, pull
request, tag, or manual dispatch, and how that entrypoint fans out into
repository checks, package matrices, or documentation publication.

The top-level entrypoints are `verify.yml` for pushes and pull requests,
`deploy-docs.yml` for handbook publication from `main`, and the release split
workflows (`release-github.yml`, `release-pypi.yml`, `release-ghcr.yml`) for
tag-driven publication. `ci.yml` and `release-artifacts.yml` are reusable
workflows called by those entrypoints rather than standalone manual surfaces.

## Pages in This Section

- [verify](verify.md)
- [reusable-workflows](reusable-workflows.md)
- [deploy-docs](deploy-docs.md)
- [release-workflows](release-workflows.md)

## Purpose

Use this section to find the workflow file, trigger, and job tree behind a
repository automation concern.

## Stability

Keep it aligned with the actual workflow files in `.github/workflows/`.
