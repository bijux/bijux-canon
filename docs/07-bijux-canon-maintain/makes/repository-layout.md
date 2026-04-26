---
title: Repository Layout
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-09
---

# Repository Layout

The make layout is part of the repository architecture.

The `makes/` tree separates shared concepts instead of mixing every target into
one file. Repository-wide fragments live near the root, reusable `bijux-py`
logic lives under `makes/bijux-py/`, and package-facing entry files live under
`makes/packages/`.

## Layout Anchors

- `makes/root.mk`, `makes/env.mk`, and `makes/packages.mk` at the repository
  layer
- `makes/bijux-py/root/` for root target groups
- `makes/bijux-py/repository/` for repository contracts
- `makes/bijux-py/ci/` for CI target families
- `makes/packages/` for package-specific bindings

## Reader Route

- open this page when the main question is how the `makes/` tree is partitioned
- open `https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/environment-model/`
  for shared environment fragments
- open `https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/package-contracts/`
  for reusable package-level target contracts

