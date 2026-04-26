---
title: Repository Fit
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Repository Fit

`bijux-canon-agent` is a separate package because orchestration creates its own readability and contract pressure. Keeping it visible stops workflow logic from hiding inside reasoning code or runtime policy.

## Why This Is A Package

- `packages/bijux-canon-agent/src/bijux_canon_agent` makes orchestration ownership visible in code
- `packages/bijux-canon-agent/tests` proves determinism and trace quality at the package seam
- `packages/bijux-canon-agent/apis` shows where orchestration behavior becomes a tracked public surface

## First Proof Check

- `packages/bijux-canon-agent/pyproject.toml` for publishable package identity
- `packages/bijux-canon-agent/README.md` for package-level reader framing
- `packages/bijux-canon-agent/tests` for executable proof that the seam still matters

## Fit Warning

If the package can only be defended as “where the workflow code lives,” the orchestration seam has not been explained well enough.

## Bottom Line

The repository should make the `bijux-canon-agent` seam easier to defend, not easier to forget.
