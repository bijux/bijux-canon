---
title: Repository Fit
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Repository Fit

`bijux-canon-runtime` is a separate package because run authority is its own system seam. The repository needs one place where persistence, replay, and acceptance policy are explicit and reviewable.

## Why This Is A Package

- `packages/bijux-canon-runtime/src/bijux_canon_runtime/application/execute_flow.py` shows the authority entrypoints
- `packages/bijux-canon-runtime/src/bijux_canon_runtime/observability` exposes the durable replay surfaces
- `packages/bijux-canon-runtime/tests` proves authority claims against acceptance and persistence behavior

## First Proof Check

- `packages/bijux-canon-runtime/pyproject.toml` for publishable package identity
- `packages/bijux-canon-runtime/README.md` for package-level reader framing
- `packages/bijux-canon-runtime/tests` for executable proof that the seam still matters

## Fit Warning

If the package is justified only because it runs last, the authority seam has collapsed into execution order.

## Bottom Line

The repository should make the `bijux-canon-runtime` seam easier to defend, not easier to forget.
