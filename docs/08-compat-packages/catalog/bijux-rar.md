---
title: bijux-rar
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# bijux-rar

`bijux-rar` remains published so existing environments can keep installing the
legacy reasoning distribution name while moving toward `bijux-canon-reason`.

It is a migration surface, not the preferred package for new work. New
installations should start with `bijux-canon-reason`.

## Canonical replacement

- distribution: `bijux-canon-reason`
- Python import: `bijux_canon_reason`
- command: `bijux-canon-reason`
- package handbook: <https://bijux.io/bijux-canon/bijux-canon-reason/>

## What the compatibility package preserves

- the published `bijux-rar` distribution name on PyPI
- the `bijux_rar` Python import surface
- the `bijux-rar` console command

## Migration direction

- install `bijux-canon-reason` for new environments
- keep `bijux-rar` only while existing automation still depends on the legacy
  name
- use the shared migration handbook for rename planning and retirement review:
  <https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/>

## Repository transition

The former standalone repository at <https://github.com/bijux/bijux-rar> is
being retired in favor of the unified monorepo at
<https://github.com/bijux/bijux-canon>.
