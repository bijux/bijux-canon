---
title: Environment Model
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-09
---

# Environment Model

The make system should make environment assumptions visible.

Repository make behavior depends on shared environment fragments such as
`makes/env.mk`, `makes/bijux-py/root/env.mk`, and
`makes/bijux-py/repository/env.mk`. These files define the variables and
execution assumptions that later targets rely on.

## Environment Rules

- centralize shared variables instead of redefining them across many target
  files
- keep package-independent environment logic in shared fragments
- name environment expectations clearly enough that CI and local runs are easy
  to compare

## Purpose

This page explains where shared environment expectations live in the make
system.

## Stability

Keep it aligned with the actual environment fragments under `makes/`.
