---
title: deploy-docs
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-09
---

# deploy-docs

`deploy-docs.yml` is the workflow that turns the checked-in handbook into the
published site.

It matters because documentation in this repository is treated as a maintained
surface, not as an optional by-product. The deploy workflow is therefore part
of the documentation contract, not a secondary convenience step.

## Workflow Anchors

- `.github/workflows/deploy-docs.yml`
- `mkdocs.yml` and `mkdocs.shared.yml`
- `docs/` as the published source tree

## Purpose

This page records the role of the docs deployment workflow.

## Stability

Keep it aligned with the docs deployment workflow and the published handbook
inputs it relies on.
