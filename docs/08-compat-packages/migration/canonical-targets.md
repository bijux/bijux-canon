---
title: Canonical Targets
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# Canonical Targets

Migration gets easier when the destination is named as clearly as the legacy
source. Every compatibility package should point at one canonical package and
one handbook route without ambiguity.

## Current Target Map

- `agentic-flows` -> `bijux-canon-runtime` -> <https://bijux.io/bijux-canon/06-bijux-canon-runtime/>
- `bijux-agent` -> `bijux-canon-agent` -> <https://bijux.io/bijux-canon/05-bijux-canon-agent/>
- `bijux-rag` -> `bijux-canon-ingest` -> <https://bijux.io/bijux-canon/02-bijux-canon-ingest/>
- `bijux-rar` -> `bijux-canon-reason` -> <https://bijux.io/bijux-canon/04-bijux-canon-reason/>
- `bijux-vex` -> `bijux-canon-index` -> <https://bijux.io/bijux-canon/03-bijux-canon-index/>

## Targeting Rules

- new dependencies should use the canonical distribution name
- new code should use canonical imports and commands
- package docs should route immediately to the canonical handbook once the
  target is known

## First Proof Check

- compatibility package `README.md` files
- canonical package docs under `docs/02-...` through `docs/06-...`
