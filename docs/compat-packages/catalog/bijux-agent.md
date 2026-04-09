---
title: bijux-agent
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# bijux-agent

`bijux-agent` remains published so existing environments can keep installing
the legacy agent distribution name while moving toward `bijux-canon-agent`.

It is a migration surface, not the preferred package for new work. New
installations should start with `bijux-canon-agent`.

## Canonical replacement

- distribution: `bijux-canon-agent`
- Python import: `bijux_canon_agent`
- command: `bijux-canon-agent`
- package handbook: <https://bijux.io/bijux-canon/bijux-canon-agent/>

## What the compatibility package preserves

- the published `bijux-agent` distribution name on PyPI
- the `bijux_agent` Python import surface
- the `bijux-agent` console command

## Migration direction

- install `bijux-canon-agent` for new environments
- keep `bijux-agent` only while existing automation still depends on the
  legacy name
- use the shared migration handbook for rename planning and retirement review:
  <https://bijux.io/bijux-canon/compat-packages/migration/migration-guidance/>

## Repository transition

The former standalone repository at <https://github.com/bijux/bijux-agent> is
being retired in favor of the unified monorepo at
<https://github.com/bijux/bijux-canon>.
