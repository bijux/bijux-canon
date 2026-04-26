---
title: Repository Layout
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Repository Layout

The `makes/` tree is part of repository architecture. Its layout separates
repository assembly, reusable contracts, CI target families, and package
bindings so the command surface stays reviewable.

## Layout Layers

- `makes/root.mk`, `makes/env.mk`, and `makes/packages.mk` at the repository
  layer
- `makes/bijux-py/root/` for root target groups and shared routing
- `makes/bijux-py/repository/` for repository contract fragments
- `makes/bijux-py/ci/` for CI target families
- `makes/packages/` for canonical and compatibility package bindings

## Why Layout Is Policy

The directory split is not decorative. It tells the reviewer whether a change
is introducing repository policy, a reusable contract, or a package binding.
Mixing those layers makes target ownership less honest.

## First Proof Check

- `makes/bijux-py/repository/`
- `makes/bijux-py/ci/`
- `makes/packages/`
