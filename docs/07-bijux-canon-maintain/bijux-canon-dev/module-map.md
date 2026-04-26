---
title: Module Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Module Map

The maintainer package is organized by repository-health responsibility. That
layout is part of the review model because it lets a contributor find the right
helper module before changing a shared rule.

## Module Roots

- `src/bijux_canon_dev/api` for schema drift and API freeze contracts
- `src/bijux_canon_dev/quality` for dependency and repository quality checks
- `src/bijux_canon_dev/security` for security gates such as `pip-audit`
- `src/bijux_canon_dev/release` for publication guards and version resolution
- `src/bijux_canon_dev/sbom` for requirements and SBOM generation support
- `src/bijux_canon_dev/docs` for docs publication and docs catalog support
- `src/bijux_canon_dev/packages` for package-specific maintenance adapters
- `src/bijux_canon_dev/trusted_process.py` for shared trusted-process helpers

## How Work Flows

Most maintainer rules follow the same path: a checked-in helper module enforces
a repository rule, tests prove the helper, and `make` or GitHub Actions call
that helper at review or release time. The package structure should keep that
path obvious instead of hiding it behind shell glue.

## First Proof Check

- `packages/bijux-canon-dev/src/bijux_canon_dev`
- `packages/bijux-canon-dev/tests/test_*.py`
- consumers in `Makefile`, `makes/`, and `.github/workflows/`
