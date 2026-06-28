---
title: bijux-canon
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-06-28
---

# bijux-canon

`bijux-canon` remains published so existing environments can keep using the
shorter family-root runtime name while the canonical package stays
`bijux-canon-runtime`. New work should start at the canonical package, not
here.

## Canonical Target

- distribution: `bijux-canon-runtime`
- Python import: `bijux_canon_runtime`
- command: `bijux-canon-runtime`
- package handbook: <https://bijux.io/bijux-canon/06-bijux-canon-runtime/>

## Preserved Surfaces

- the published `bijux-canon` distribution name
- the `bijux_canon` Python import surface
- the `bijux-canon` command name

## When To Keep It

Keep `bijux-canon` only while a documented dependent environment still relies
on the shorter family-root name. Once installs, imports, and command usage move
to `bijux-canon-runtime`, the compatibility package becomes retirement debt.

## First Proof Check

- `packages/compat-bijux-canon`
- the compatibility package `README.md`
- the canonical handbook at <https://bijux.io/bijux-canon/06-bijux-canon-runtime/>
- shared retirement rules in
  <https://bijux.io/bijux-canon/08-compat-packages/migration/retirement-conditions/>

## Repository Fit

This alias does not stand in for a retired standalone repository. It preserves
the shorter runtime family-root distribution inside the consolidated
`bijux-canon` repository.
