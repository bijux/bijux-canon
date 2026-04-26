---
title: release-workflows
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-19
---

# release-workflows

`release-artifacts.yml` orchestrates tag-driven publication and calls
`release-github.yml`, `release-pypi.yml`, and `release-ghcr.yml` as reusable
workflow surfaces.

The split keeps each publication surface explicit:

- `release-pypi.yml` governs PyPI publication behavior
- `release-ghcr.yml` governs GHCR bundle publication behavior
- `release-github.yml` governs GitHub Release publication behavior
- `release-artifacts.yml` orchestrates build + publish order for
  tag-driven releases

## Workflow Anchors

- `.github/workflows/release-artifacts.yml`
- `.github/workflows/release-github.yml`
- `.github/workflows/release-pypi.yml`
- `.github/workflows/release-ghcr.yml`
- package release metadata and staged release assets

## Current Job Tree

- `release-artifacts.yml`: build matrix + reusable release workflow
  orchestration
- `release-pypi.yml`: `resolve` + publication jobs for configured package inputs
- `release-ghcr.yml`: `resolve` + per-package GHCR artifact publication
- `release-github.yml`: release planning + GitHub Release publication

## Reader Route

- read this page when the main question is which release surfaces are published
  and how tag-driven release flow is split
- continue to `https://bijux.io/bijux-canon/07-bijux-canon-maintain/gh-workflows/reusable-workflows/`
  for the reusable workflow layer behind publication
- continue to `https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/release-support/`
  for the maintainer package helpers that support release behavior

