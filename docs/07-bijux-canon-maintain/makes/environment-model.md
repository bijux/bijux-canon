---
title: Environment Model
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Environment Model

The make system keeps environment assumptions visible so local and CI behavior
can be compared without guesswork. Shared variables and execution defaults live
in named fragments instead of being redefined opportunistically.

## Shared Environment Files

- `makes/env.mk` for repository-wide defaults
- `makes/bijux-py/root/env.mk` for shared Python-root assumptions
- `makes/bijux-py/repository/env.mk` for repository contract environment setup

## Review Rule

Environment logic should move upward into shared fragments when multiple targets
depend on it. Repeating the same variable or shell assumption across target
files makes failures harder to explain and easier to drift.

## First Proof Check

- `makes/env.mk`
- `makes/bijux-py/root/env.mk`
- `makes/bijux-py/repository/env.mk`
