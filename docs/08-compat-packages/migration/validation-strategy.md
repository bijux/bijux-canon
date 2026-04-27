---
title: Validation Strategy
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# Validation Strategy

Compatibility packages are small, but they still need proof. Their trust comes
from naming continuity, correct metadata, and clear routing to the canonical
package, so validation has to check those exact surfaces.

## Validation Focus

- import resolution
- packaging metadata correctness
- canonical target routing in docs and README files
- repository-wide evidence that migration is moving forward

## Useful Checks

- repository-wide `rg` searches for legacy names
- package tests or smoke checks that confirm preserved imports still resolve
- release and metadata checks that keep canonical targets explicit

## First Proof Check

- `packages/compat-*`
- compatibility package `README.md` files
- repository validation commands and search evidence
