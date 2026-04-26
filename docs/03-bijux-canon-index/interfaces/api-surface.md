---
title: API Surface
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# API Surface

The API surface for `bijux-canon-index` is where caller-visible HTTP or schema behavior becomes a contract. If the API shape for retrieval behavior matters, it should be traceable to tracked schemas and owning modules.

## What To Check

- start with the tracked schema surface: `apis/bijux-canon-index/v1/schema.yaml`
- name the modules that actually own the caller-visible behavior
- treat undocumented response or request shapes as unstable until proven otherwise

## First Proof Check

- `src` and boundary-facing modules for the owning implementation surface
- `apis/bijux-canon-index/v1/schema.yaml` or tracked examples for the documented contract surface
- `tests` for executable confirmation that the contract still holds

## Bottom Line

If callers depend on `bijux-canon-index` for retrieval behavior, the contract needs to be named as clearly as the implementation.
