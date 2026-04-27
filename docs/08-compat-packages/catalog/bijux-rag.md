---
title: bijux-rag
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# bijux-rag

`bijux-rag` remains published so existing environments can keep using the legacy
ingest package name while migrating toward `bijux-canon-ingest`. New work should start at
the canonical package, not here.

## Canonical Target

- distribution: `bijux-canon-ingest`
- Python import: `bijux_canon_ingest`
- command: `bijux-canon-ingest`
- package handbook: <https://bijux.io/bijux-canon/02-bijux-canon-ingest/>

## Preserved Surfaces

- the published `bijux-rag` distribution name
- the `bijux_rag` Python import surface
- the `bijux-rag` command name

## When To Keep It

Keep `bijux-rag` only while a documented dependent environment still relies on
the legacy name. Once installs, imports, and command usage move to `bijux-canon-ingest`,
the compatibility package becomes retirement debt.

## First Proof Check

- `packages/compat-bijux-rag`
- the compatibility package `README.md`
- the canonical handbook at <https://bijux.io/bijux-canon/02-bijux-canon-ingest/>
- shared retirement rules in
  <https://bijux.io/bijux-canon/08-compat-packages/migration/retirement-conditions/>

## Repository Transition

The former standalone repository at <https://github.com/bijux/bijux-rag> is retired in favor of
<https://github.com/bijux/bijux-canon>. The legacy package remains only as a
bridge to the canonical package inside the monorepo.
