---
title: CI Targets
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-09
---

# CI Targets

The CI make surface stays explicit so workflow files are not the only place
where verification logic can be understood.

The repository groups CI-oriented make fragments under `makes/bijux-py/ci/`.
Those files define target families for docs, lint, quality, sbom, security,
test, and build-related work.

## CI Anchors

- `makes/bijux-py/ci/build.mk`
- `makes/bijux-py/ci/docs.mk`
- `makes/bijux-py/ci/lint.mk`
- `makes/bijux-py/ci/quality.mk`
- `makes/bijux-py/ci/security.mk`
- `makes/bijux-py/ci/test.mk`

## Reader Route

- open this page when the main question is where CI-oriented make targets live
- open `https://bijux.io/bijux-canon/07-bijux-canon-maintain/gh-workflows/verify/`
  for the workflow that calls repository and package verification
- open `https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/repository-layout/`
  for the wider `makes/` tree layout

