---
title: CI Targets
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# CI Targets

The CI make surface keeps verification logic understandable outside workflow
YAML. Shared CI targets live under `makes/bijux-py/ci/` so a maintainer can see
what kinds of checks exist before reading the workflow matrix.

## CI Target Families

- `makes/bijux-py/ci/build.mk`
- `makes/bijux-py/ci/docs.mk`
- `makes/bijux-py/ci/lint.mk`
- `makes/bijux-py/ci/quality.mk`
- `makes/bijux-py/ci/sbom.mk`
- `makes/bijux-py/ci/security.mk`
- `makes/bijux-py/ci/test.mk`

## Workflow Handoff

Workflows such as `verify.yml` call repository and package checks, but the make
files still define the families of work being run. That split matters because a
reviewer should be able to inspect the check surface without treating workflow
jobs as the only source of truth.

## First Proof Check

- `makes/bijux-py/ci/`
- `.github/workflows/verify.yml`
- callers in reusable workflow files
