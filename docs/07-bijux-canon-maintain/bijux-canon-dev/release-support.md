---
title: Release Support
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Release Support

Shared release helpers live in `bijux-canon-dev` so publication rules stay
consistent across packages. Release support should feel mechanical and visible,
not magical: a reviewer should be able to trace the rule from helper code to
test to workflow.

## Shared Release Helpers

- `release/version_resolver.py` for package version resolution
- `release/publication_guard.py` for publication safety checks
- tests such as `test_publish_metadata.py`, `test_release_artifacts.py`,
  `test_release_history.py`, and `test_release_publication.py`

## Release Threshold

A release helper is repository scope only when it protects a rule shared by
multiple packages. If the logic mainly explains one package's artifact or
version behavior, that detail belongs in the package handbook even if the
workflow calls shared code.

## First Proof Check

- `packages/bijux-canon-dev/src/bijux_canon_dev/release`
- `packages/bijux-canon-dev/tests/test_publish_metadata.py`
- `packages/bijux-canon-dev/tests/test_release_publication.py`
- release callers in `.github/workflows/`

## Boundary

Release support here explains shared publication discipline. Product package
release meaning still belongs in the owning package docs.
