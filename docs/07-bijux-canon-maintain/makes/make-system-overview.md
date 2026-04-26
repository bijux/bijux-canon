---
title: Make System Overview
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Make System Overview

The repository make system is the shared command language for local work, CI,
package dispatch, and release preparation. It begins at `Makefile` and becomes
more specific as responsibility moves into root fragments, reusable contracts,
and package bindings.

## Core Layers

- `Makefile` for the top-level entrypoint
- `makes/root.mk` for repository assembly
- `makes/env.mk` and `makes/packages.mk` for shared environment and package
  catalog setup
- `makes/bijux-py/` for reusable contracts and target families
- `makes/packages/` for canonical and compatibility package bindings

## Why Layering Matters

A layered make tree keeps command ownership visible. A reviewer can tell whether
a target is repository policy, reusable infrastructure, package dispatch, or a
package-local binding instead of treating `make` as a bag of aliases.

## First Proof Check

- `Makefile`
- `makes/root.mk`
- `makes/bijux-py/`
- `makes/packages/`
