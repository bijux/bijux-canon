---
title: Configuration Surface
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Configuration Surface

Configuration is part of the contract when it changes how `bijux-canon-index` exposes retrieval behavior. Operators should be able to tell what may vary without reading code.

## What To Check

- name the settings that intentionally change package behavior
- separate supported configuration from internal toggles and development shortcuts
- update docs and tests when configuration changes caller-visible behavior

## First Proof Check

- `src` and boundary-facing modules for the owning implementation surface
- `apis/bijux-canon-index/v1/schema.yaml` or tracked examples for the documented contract surface
- `tests` for executable confirmation that the contract still holds

## Bottom Line

If callers depend on `bijux-canon-index` for retrieval behavior, the contract needs to be named as clearly as the implementation.
