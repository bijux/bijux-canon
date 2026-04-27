---
title: bijux-rar
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# bijux-rar

`bijux-rar` remains published so existing environments can keep using the legacy
reasoning package name while migrating toward `bijux-canon-reason`. New work should start at
the canonical package, not here.

## Canonical Target

- distribution: `bijux-canon-reason`
- Python import: `bijux_canon_reason`
- command: `bijux-canon-reason`
- package handbook: <https://bijux.io/bijux-canon/04-bijux-canon-reason/>

## Preserved Surfaces

- the published `bijux-rar` distribution name
- the `bijux_rar` Python import surface
- the `bijux-rar` command name

## When To Keep It

Keep `bijux-rar` only while a documented dependent environment still relies on
the legacy name. Once installs, imports, and command usage move to `bijux-canon-reason`,
the compatibility package becomes retirement debt.

## First Proof Check

- `packages/compat-bijux-rar`
- the compatibility package `README.md`
- the canonical handbook at <https://bijux.io/bijux-canon/04-bijux-canon-reason/>
- shared retirement rules in
  <https://bijux.io/bijux-canon/08-compat-packages/migration/retirement-conditions/>

## Repository Transition

The former standalone repository at <https://github.com/bijux/bijux-rar> is retired in favor of
<https://github.com/bijux/bijux-canon>. The legacy package remains only as a
bridge to the canonical package inside the monorepo.
