---
title: verify
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-19
---

# verify

`verify.yml` is the main repository verification workflow.

It is the workflow that decides whether repository automation contracts and the
package matrix are healthy enough to trust on pushes and pull requests. It is
therefore the broadest CI truth for day-to-day repository changes.

The job tree is intentionally split. `repository` runs shared automation
contracts first, `package` fans out by package through `ci.yml`, and
each reusable package run splits again into package-scoped `tests`, `checks`,
and `lint` jobs.

## Workflow Anchors

- `.github/workflows/verify.yml`
- repository contract checks driven from `make`
- the package matrix that delegates to reusable package workflows

## Reader Route

- read this page when the main question is how repository verification runs on
  pushes and pull requests
- continue to `https://bijux.io/bijux-canon/07-bijux-canon-maintain/gh-workflows/reusable-workflows/`
  for the reusable workflow building blocks behind the package matrix
- continue to `https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/ci-targets/`
  for the make-layer target families behind the workflow

## Purpose

This page shows when verification runs and how it branches from repository
checks into package-level jobs.

## Stability

Keep it aligned with the real trigger paths, repository job, and package matrix
declared in `verify.yml`.
