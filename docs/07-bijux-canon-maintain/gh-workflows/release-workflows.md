---
title: release-workflows
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-10
---

# release-workflows

`release-github.yml`, `release-pypi.yml`, and `release-ghcr.yml` replace the
legacy single `publish.yml` entrypoint.

The split keeps each publication surface explicit:

- `release-pypi.yml` governs PyPI publication behavior
- `release-ghcr.yml` governs GHCR bundle publication behavior
- `release-github.yml` governs GitHub Release publication behavior
- `release-orchestrator.yml` orchestrates build + publish order for
  tag-driven releases

## Workflow Anchors

- `.github/workflows/release-orchestrator.yml`
- `.github/workflows/release-github.yml`
- `.github/workflows/release-pypi.yml`
- `.github/workflows/release-ghcr.yml`
- `.github/workflows/build-release-artifacts.yml`
- package release metadata and staged release assets

## Current Job Tree

- `release-orchestrator.yml`: build matrix + reusable release workflow
  orchestration
- `release-pypi.yml`: `resolve` + publication jobs for configured package inputs
- `release-ghcr.yml`: `resolve` + per-package GHCR artifact publication
- `release-github.yml`: release planning + GitHub Release publication

## Purpose

Use this page to understand which release surfaces are published and how the
tag-driven workflow split is organized.

## Stability

Keep it aligned with the three release workflows and their shared artifact and
release configuration contracts.
