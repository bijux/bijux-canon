---
title: Root Entrypoints
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Root Entrypoints

Root make entrypoints should be obvious enough that maintainers do not have to
memorize hidden aliases. The command surface starts at a small number of files
that define the shared environment and dispatch model.

## Root Entrypoints

- `Makefile` includes `makes/root.mk`
- `makes/root.mk` assembles repository-level fragments
- `makes/env.mk` defines shared environment assumptions
- `makes/packages.mk` loads package metadata and bindings

## What Starts Here

These files decide how repository-wide targets become concrete package or CI
work. If root entrypoints are unclear, every downstream fragment becomes harder
to review.

## First Proof Check

- `Makefile`
- `makes/root.mk`
- `makes/env.mk`
- `makes/packages.mk`
