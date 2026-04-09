---
title: makes
audience: mixed
type: index
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-09
---

# makes

The `makes/` section explains the shared Make surface that ties repository
operations together.

The make system is a real interface in this repository. It is how local work,
CI checks, package dispatch, and release-oriented automation are exposed in a
repeatable way. These pages should help a maintainer see the structure behind
those targets instead of treating the make layer as a flat bag of commands.

## Pages in This Section

- [Make System Overview](make-system-overview.md)
- [Root Entrypoints](root-entrypoints.md)
- [Environment Model](environment-model.md)
- [Repository Layout](repository-layout.md)
- [Package Dispatch](package-dispatch.md)
- [CI Targets](ci-targets.md)
- [Package Contracts](package-contracts.md)
- [Release Surfaces](release-surfaces.md)
- [Authoring Rules](authoring-rules.md)

## Purpose

This page routes maintainers into the make-system documentation without forcing
them to infer the structure from file names alone.

## Stability

Keep it aligned with the actual make surfaces the repository expects people and
automation to use.
