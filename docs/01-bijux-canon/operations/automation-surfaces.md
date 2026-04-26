---
title: Automation Surfaces
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-09
---

# Automation Surfaces

Repository automation should be visible in named surfaces, not hidden behind
tribal shortcuts.

The repository already exposes its shared operational machinery through a small
set of durable entrypoints. Keeping those surfaces explicit matters because they
shape how contributors learn the workspace and how reviewers reason about the
impact of shared changes.

## Core Automation Surfaces

- `Makefile` as the top-level repository entrypoint
- `makes/` as the structured library of shared make fragments
- `.github/workflows/` as the published CI, docs, and release automation
- `packages/bijux-canon-dev` as the code-bearing home for maintainer helpers

## Automation Rule

If automation changes repository-wide behavior, it should be explainable from
one or more of these surfaces without reading unrelated shell glue first.

## Review Lens

- does the automation name what it touches
- is the owning file obvious from the docs and the command shape
- does the change keep package ownership visible instead of burying it in root
  convenience logic

## Open This Page When

- you need to locate the repository entrypoint behind a shared command,
  workflow, or helper
- you are checking whether automation belongs in a root surface or in a package
- you want the shortest map of the repository's shared operational machinery

## Decision Rule

Keep shared automation in named, inspectable surfaces. If a workflow or helper
changes repository-wide behavior, a reader should be able to trace it from one
of the surfaces listed here without reverse-engineering stray shell glue first.

## Purpose

This page shows where repository automation lives so shared behavior stays
inspectable and reviewable.

## Stability

Keep it aligned with the actual automation surfaces that contributors are
expected to use.
