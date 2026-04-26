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

It runs on `main` when docs-related files change and can also be started
manually. The job tree stays small on purpose: build the strict site, validate
the published assets, then deploy the Pages artifact.

## Workflow Anchors

- `.github/workflows/deploy-docs.yml`
- `mkdocs.yml` and `mkdocs.shared.yml`
- `docs/` as the published source tree

## Reader Route

- read this page when the main question is how the checked-in handbook becomes
  the published site
- continue to `https://bijux.io/bijux-canon/01-bijux-canon/foundation/documentation-system/`
  for the published handbook structure
- continue to `https://bijux.io/bijux-canon/07-bijux-canon-maintain/gh-workflows/verify/`
  when the question turns into verification rather than publication

## Purpose

This page shows when documentation publication runs and which site inputs it
validates before deploy.

## Stability

Keep it aligned with the docs deployment workflow and the published handbook
inputs it relies on.
