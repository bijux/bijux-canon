---
title: Data Contracts
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Data Contracts

Data contracts for `bijux-canon-agent` cover the structured payloads another tool or package may parse, store, compare, or replay. If a shape matters outside one function call, it should be named explicitly.

## What To Check

- name the stable payload shapes behind workflow traces, role outputs, and agent artifacts
- separate internal working models from exported or downstream-consumed structures
- treat silent payload drift as a compatibility event, not a cosmetic change

## First Proof Check

- `src` and boundary-facing modules for the owning implementation surface
- `apis/bijux-canon-agent/v1/schema.yaml` or tracked examples for the documented contract surface
- `tests` for executable confirmation that the contract still holds

## Bottom Line

If callers depend on `bijux-canon-agent` for orchestration behavior, the contract needs to be named as clearly as the implementation.
