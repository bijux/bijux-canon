---
title: Deployment Boundaries
audience: mixed
type: guide
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-04
---

# Deployment Boundaries

Deployment for `bijux-canon-runtime` should respect the package boundary instead of assuming the full repository is always present.

## Boundary Facts

- package root: `packages/bijux-canon-runtime`
- public metadata: `packages/bijux-canon-runtime/pyproject.toml`
- release notes: `packages/bijux-canon-runtime/CHANGELOG.md` when present

## Purpose

This page reminds maintainers that packages are publishable units, not just folders in one repo.

## Stability

Keep it aligned with the package's actual distributable surface.
