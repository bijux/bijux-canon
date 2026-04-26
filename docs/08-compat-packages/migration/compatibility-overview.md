---
title: Compatibility Overview
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# Compatibility Overview

The compatibility layer exists to reduce migration breakage while the canonical
`bijux-canon-*` family becomes the only normal starting point for new work.
Preserving an old public name is sometimes necessary, but it is still debt that
should stay visible.

## Preserved Surfaces

- legacy distribution names
- legacy Python import names
- legacy command names where those still exist

## Bridge Rule

A preserved legacy surface is acceptable only when it shields a real supported
environment during migration. The bridge loses legitimacy as soon as it becomes
an excuse to postpone migration indefinitely.

## First Proof Check

- `packages/compat-*`
- compatibility package `README.md` targets
- migration validation and retirement pages
