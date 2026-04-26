---
title: Automation Surfaces
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Automation Surfaces

Repository automation should be visible in named surfaces, not hidden behind
tribal shortcuts.

## Automation Order

Read shared automation in this order:

1. `Makefile` for the top-level entrypoint a maintainer is expected to start from
2. `makes/` for the structured library behind shared commands
3. `.github/workflows/` for published verification, docs, and release execution
4. `packages/bijux-canon-dev` for code-bearing maintainer helpers

## Why The Order Matters

A top-level command is usually the fastest operational route. A workflow file is
usually the fastest route when the question starts from CI. `bijux-canon-dev`
should explain helper behavior, not hide the only honest owner of a repository
rule.

## Failure Signals

- a contributor cannot tell which root command is canonical for common work
- a workflow changes repository-wide behavior but the owning file is not easy to name
- a helper script starts carrying product logic that belongs in one package

## Bottom Line

Shared automation is healthy when a reader can name the owning surface quickly
and trace the behavior without reverse-engineering stray shell glue first.
