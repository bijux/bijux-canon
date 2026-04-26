---
title: Dependency Continuity
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# Dependency Continuity

Compatibility packages succeed only when they preserve continuity while still
pushing environments toward canonical names. The promise should stay narrow: the
legacy package keeps installs, imports, or commands alive long enough to finish
migration.

## Continuity Rules

- preserve a legacy name only while supported environments still need it
- keep compatibility metadata aligned with the matching canonical package
- point dependency, import, and command migrations toward the canonical package
  without mixed messaging

## Review Questions

- which supported environment still needs the legacy name
- whether package metadata and docs still identify the canonical target clearly
- whether continuity is acting as a bridge or as a substitute for migration work

## First Proof Check

- `packages/compat-*`
- compatibility package metadata and README files
- repository-wide searches for remaining legacy names
