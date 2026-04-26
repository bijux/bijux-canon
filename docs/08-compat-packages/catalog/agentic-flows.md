---
title: agentic-flows
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# agentic-flows

`agentic-flows` remains published so existing environments can keep using the legacy
runtime package name while migrating toward `bijux-canon-runtime`. New work should start at
the canonical package, not here.

## Canonical Target

- distribution: `bijux-canon-runtime`
- Python import: `bijux_canon_runtime`
- command: `bijux-canon-runtime`
- package handbook: <https://bijux.io/bijux-canon/06-bijux-canon-runtime/>

## Preserved Surfaces

- the published `agentic-flows` distribution name
- the `agentic_flows` Python import surface
- the `agentic-flows` command name

## When To Keep It

Keep `agentic-flows` only while a documented dependent environment still relies on
the legacy name. Once installs, imports, and command usage move to `bijux-canon-runtime`,
the compatibility package becomes retirement debt.

## First Proof Check

- `packages/compat-agentic-flows`
- the compatibility package `README.md`
- the canonical handbook at <https://bijux.io/bijux-canon/06-bijux-canon-runtime/>
- shared retirement rules in
  <https://bijux.io/bijux-canon/08-compat-packages/migration/retirement-conditions/>

## Repository Transition

The former standalone repository at <https://github.com/bijux/agentic-flows> is retired in favor of
<https://github.com/bijux/bijux-canon>. The legacy package remains only as a
bridge to the canonical package inside the monorepo.
