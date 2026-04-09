---
title: Release Surfaces
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-09
---

# Release Surfaces

Release-facing make behavior should be visible before it is triggered from CI.

The repository keeps release-related make logic in places such as
`makes/publish.mk`, `makes/bijux-py/repository/publish.mk`, and the build and
sbom fragments that shape artifact creation. These surfaces should make release
behavior understandable outside the workflow YAML that eventually invokes them.

## Release Anchors

- `makes/publish.mk`
- `makes/bijux-py/repository/publish.mk`
- `makes/bijux-py/ci/build.mk`
- `makes/bijux-py/ci/sbom.mk`

## Purpose

This page records the main make files that influence release preparation and
publication behavior.

## Stability

Keep it aligned with the repository’s actual release-facing make surfaces.
