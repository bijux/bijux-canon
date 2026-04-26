---
title: bijux-vex
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# bijux-vex

`bijux-vex` remains published so existing environments can keep using the legacy
index package name while migrating toward `bijux-canon-index`. New work should start at
the canonical package, not here.

## Canonical Target

- distribution: `bijux-canon-index`
- Python import: `bijux_canon_index`
- command: `bijux-canon-index`
- package handbook: <https://bijux.io/bijux-canon/03-bijux-canon-index/>

## Preserved Surfaces

- the published `bijux-vex` distribution name
- the `bijux_vex` Python import surface
- the `bijux-vex` command name

## When To Keep It

Keep `bijux-vex` only while a documented dependent environment still relies on
the legacy name. Once installs, imports, and command usage move to `bijux-canon-index`,
the compatibility package becomes retirement debt.

## First Proof Check

- `packages/compat-bijux-vex`
- the compatibility package `README.md`
- the canonical handbook at <https://bijux.io/bijux-canon/03-bijux-canon-index/>
- shared retirement rules in
  <https://bijux.io/bijux-canon/08-compat-packages/migration/retirement-conditions/>

## Repository Transition

The former standalone repository at <https://github.com/bijux/bijux-vex> is retired in favor of
<https://github.com/bijux/bijux-canon>. The legacy package remains only as a
bridge to the canonical package inside the monorepo.
