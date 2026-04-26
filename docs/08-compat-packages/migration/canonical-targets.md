---
title: Canonical Targets
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-09
---

# Canonical Targets

Migration gets easier when the destination is named just as clearly as the
legacy source.

The compatibility layer exists to bridge old public names to the canonical
package family. That bridge only works if the target package is unmistakable
and the target docs are the place where new work is expected to begin.

## Current Target Map

- `agentic-flows` migrates to `bijux-canon-runtime`
- `bijux-agent` migrates to `bijux-canon-agent`
- `bijux-rag` migrates to `bijux-canon-ingest`
- `bijux-rar` migrates to `bijux-canon-reason`
- `bijux-vex` migrates to `bijux-canon-index`

## Targeting Rules

- new dependencies should use the canonical distribution name
- new code should rely on canonical imports and canonical docs
- compatibility packages should point readers toward the owning canonical
  package without ambiguity

