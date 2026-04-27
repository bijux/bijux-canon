---
title: Release Surfaces
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Release Surfaces

Release-facing make behavior should be understandable before a workflow fires.
The repository keeps publish-related logic in named make fragments so the build,
package, and SBOM path can be reviewed without depending on the Actions UI.

## Release Files

- `makes/publish.mk`
- `makes/bijux-py/repository/publish.mk`
- `makes/bijux-py/ci/build.mk`
- `makes/bijux-py/ci/sbom.mk`

## Release Boundary

The make layer prepares release work and stages repeatable command surfaces. It
does not replace the release workflows that coordinate publication, nor does it
replace package handbooks that explain release meaning.

## First Proof Check

- `makes/publish.mk`
- `makes/bijux-py/repository/publish.mk`
- release workflow callers under `.github/workflows/`
