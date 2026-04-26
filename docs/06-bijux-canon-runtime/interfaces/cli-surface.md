---
title: CLI Surface
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# CLI Surface

The CLI surface for `bijux-canon-runtime` is the command boundary operators and scripts will treat as stable first. If the command semantics for runtime authority surfaces are real, the docs should say so plainly.

## What To Check

- name the canonical command entrypoint: `bijux-canon-runtime`
- separate supported flags and behaviors from local convenience behavior
- treat scripted usage as contract pressure, not as anecdotal usage only

## First Proof Check

- `src` and boundary-facing modules for the owning implementation surface
- `apis/bijux-canon-runtime/v1/schema.yaml` or tracked examples for the documented contract surface
- `tests` for executable confirmation that the contract still holds

## Bottom Line

If callers depend on `bijux-canon-runtime` for runtime authority surfaces, the contract needs to be named as clearly as the implementation.
