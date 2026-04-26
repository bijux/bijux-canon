---
title: Environment Model
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-09
---

# Environment Model

The make system keeps environment assumptions visible.

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

## Reader Route

- open this page when the main question is where shared make environment
  assumptions live
- open `https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/repository-layout/`
  for the wider `makes/` tree layout
- open `https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/ci-targets/`
  when the question turns into CI-oriented target families

