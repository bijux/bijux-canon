---
title: Package Contracts
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Package Contracts

Shared package behavior belongs in reusable make contracts rather than in copied
target logic. These contracts make package checks and API-related targets feel
consistent across the repository.

## Shared Contracts

- `makes/bijux-py/package.mk`
- `makes/bijux-py/api.mk`
- `makes/bijux-py/api-contract.mk`
- `makes/bijux-py/api-freeze.mk`
- `makes/bijux-py/api-live-contract.mk`

## Review Rule

A contract fragment should define a reusable rule once, then let package files
bind it honestly. If several package files start carrying their own slight
variants of the same target family, the shared contract boundary is eroding.

## First Proof Check

- `makes/bijux-py/package.mk`
- `makes/bijux-py/api*.mk`
- package bindings under `makes/packages/`
