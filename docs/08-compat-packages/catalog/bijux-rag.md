---
title: bijux-rag
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# bijux-rag

`bijux-rag` remains published so existing environments can keep installing the
legacy ingest distribution name while moving toward `bijux-canon-ingest`.

It is a migration surface, not the preferred package for new work. New
installations should start with `bijux-canon-ingest`.

## Canonical replacement

- distribution: `bijux-canon-ingest`
- Python import: `bijux_canon_ingest`
- command: `bijux-canon-ingest`
- package handbook: <https://bijux.io/bijux-canon/bijux-canon-ingest/>

## What the compatibility package preserves

- the published `bijux-rag` distribution name on PyPI
- the `bijux_rag` Python import surface
- the `bijux-rag` console command

## Migration direction

- install `bijux-canon-ingest` for new environments
- keep `bijux-rag` only while existing automation still depends on the legacy
  name
- use the shared migration handbook for rename planning and retirement review:
  <https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/>

## Repository transition

The former standalone repository at <https://github.com/bijux/bijux-rag> is
being retired in favor of the unified monorepo at
<https://github.com/bijux/bijux-canon>.
