---
title: bijux-agent
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# bijux-agent

`bijux-agent` remains published so existing environments can keep using the legacy
agent package name while migrating toward `bijux-canon-agent`. New work should start at
the canonical package, not here.

## Canonical Target

- distribution: `bijux-canon-agent`
- Python import: `bijux_canon_agent`
- command: `bijux-canon-agent`
- package handbook: <https://bijux.io/bijux-canon/05-bijux-canon-agent/>

## Preserved Surfaces

- the published `bijux-agent` distribution name
- the `bijux_agent` Python import surface
- the `bijux-agent` command name

## When To Keep It

Keep `bijux-agent` only while a documented dependent environment still relies on
the legacy name. Once installs, imports, and command usage move to `bijux-canon-agent`,
the compatibility package becomes retirement debt.

## First Proof Check

- `packages/compat-bijux-agent`
- the compatibility package `README.md`
- the canonical handbook at <https://bijux.io/bijux-canon/05-bijux-canon-agent/>
- shared retirement rules in
  <https://bijux.io/bijux-canon/08-compat-packages/migration/retirement-conditions/>

## Repository Transition

The former standalone repository at <https://github.com/bijux/bijux-agent> is retired in favor of
<https://github.com/bijux/bijux-canon>. The legacy package remains only as a
bridge to the canonical package inside the monorepo.
