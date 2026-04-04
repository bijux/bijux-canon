---
title: Deployment Boundaries
audience: mixed
type: guide
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# Deployment Boundaries

Deployment for `bijux-canon-reason` should respect the package boundary instead of assuming the full repository is always present.

## Boundary Facts

- package root: `packages/bijux-canon-reason`
- public metadata: `packages/bijux-canon-reason/pyproject.toml`
- release notes: `packages/bijux-canon-reason/CHANGELOG.md` when present

## Purpose

This page reminds maintainers that packages are publishable units, not just folders in one repo.

## Stability

Keep it aligned with the package's actual distributable surface.
