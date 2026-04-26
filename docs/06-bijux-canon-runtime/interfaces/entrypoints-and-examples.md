---
title: Entrypoints and Examples
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Entrypoints and Examples

Entrypoints and examples should make the contract around `bijux-canon-runtime` concrete quickly. A reader should be able to see one real way into runtime authority surfaces without reverse-engineering the package from source alone.

## What To Check

- name the entrypoints a reader is supposed to use first
- tie examples to real commands, schemas, or artifacts instead of narrative placeholders
- treat stale examples as contract bugs because they teach callers the wrong surface

## First Proof Check

- `src` and boundary-facing modules for the owning implementation surface
- `apis/bijux-canon-runtime/v1/schema.yaml` or tracked examples for the documented contract surface
- `tests` for executable confirmation that the contract still holds

## Bottom Line

If callers depend on `bijux-canon-runtime` for runtime authority surfaces, the contract needs to be named as clearly as the implementation.
