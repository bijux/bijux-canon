---
title: agentic-flows
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# agentic-flows

`agentic-flows` remains published so existing environments can keep installing
the legacy runtime distribution name while migrating toward
`bijux-canon-runtime`.

It should be understood as a continuity surface, not the preferred package for
new work. New installations should start with `bijux-canon-runtime`.

## Canonical replacement

- distribution: `bijux-canon-runtime`
- Python import: `bijux_canon_runtime`
- command: `bijux-canon-runtime`
- package handbook: <https://bijux.io/bijux-canon/bijux-canon-runtime/>

## What the compatibility package preserves

- the published `agentic-flows` distribution name on PyPI
- the `agentic_flows` Python import surface
- the `agentic-flows` console command

## Migration direction

- install `bijux-canon-runtime` for new environments
- keep `agentic-flows` only while existing automation still depends on the
  legacy name
- use the shared migration handbook for rename planning and retirement review:
  <https://bijux.io/bijux-canon/compat-packages/migration-guidance/>

## Repository transition

The former standalone repository at <https://github.com/bijux/agentic-flows>
is being retired in favor of the unified monorepo at
<https://github.com/bijux/bijux-canon>.
