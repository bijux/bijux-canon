---
title: Repository Fit
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Repository Fit

`bijux-canon-index` is a separate package because retrieval behavior creates its own contract pressure. Keeping that pressure visible at the package boundary prevents search semantics from becoming invisible infrastructure.

## Why This Is A Package

- `packages/bijux-canon-index/src/bijux_canon_index` makes retrieval ownership visible in code
- `packages/bijux-canon-index/apis` shows where caller expectations harden into tracked surfaces
- `packages/bijux-canon-index/tests` proves replay and provenance claims against real behavior

## First Proof Check

- `packages/bijux-canon-index/pyproject.toml` for publishable package identity
- `packages/bijux-canon-index/README.md` for package-level reader framing
- `packages/bijux-canon-index/tests` for executable proof that the seam still matters

## Fit Warning

If the package only exists as a technical convenience for backend adapters, the retrieval seam is no longer being documented honestly.

## Bottom Line

The repository should make the `bijux-canon-index` seam easier to defend, not easier to forget.
