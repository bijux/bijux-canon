---
title: bijux-vex
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# bijux-vex

`bijux-vex` remains published so existing environments can keep installing the
legacy index distribution name while moving toward `bijux-canon-index`.

It is a migration surface, not the preferred package for new work. New
installations should start with `bijux-canon-index`.

## Canonical replacement

- distribution: `bijux-canon-index`
- Python import: `bijux_canon_index`
- command: `bijux-canon-index`
- package handbook: <https://bijux.io/bijux-canon/bijux-canon-index/>

## What the compatibility package preserves

- the published `bijux-vex` distribution name on PyPI
- the `bijux_vex` Python import surface
- the `bijux-vex` console command

## Migration direction

- install `bijux-canon-index` for new environments
- keep `bijux-vex` only while existing automation still depends on the legacy
  name
- use the shared migration handbook for rename planning and retirement review:
  <https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/>

## Repository transition

The former standalone repository at <https://github.com/bijux/bijux-vex> is
being retired in favor of the unified monorepo at
<https://github.com/bijux/bijux-canon>.
