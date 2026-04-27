---
title: Public Imports
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Public Imports

Public imports for `bijux-canon-reason` define which Python-facing symbols callers may depend on without reaching into internals. Import visibility should follow the contract, not accidental package layout.

## What To Check

- start with the import root: `packages/bijux-canon-reason/src/bijux_canon_reason`
- separate supported imports from merely reachable internal symbols
- treat undocumented import usage as unstable even if it currently works

## First Proof Check

- `src` and boundary-facing modules for the owning implementation surface
- `apis/bijux-canon-reason/v1/schema.yaml` or tracked examples for the documented contract surface
- `tests` for executable confirmation that the contract still holds

## Bottom Line

If callers depend on `bijux-canon-reason` for reasoning output, the contract needs to be named as clearly as the implementation.
