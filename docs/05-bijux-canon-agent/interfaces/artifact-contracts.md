---
title: Artifact Contracts
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Artifact Contracts

Artifacts from `bijux-canon-agent` become contracts when another reader, tool, or package depends on their names, layout, or semantics. Visible output alone is not enough; the stable artifact story has to be explicit.

## What To Check

- name the durable artifacts behind workflow traces, role outputs, and agent artifacts
- separate reviewable artifacts from local debug residue or incidental output
- treat path, naming, or semantic drift as compatibility pressure when downstream readers rely on it

## First Proof Check

- `src` and boundary-facing modules for the owning implementation surface
- `apis/bijux-canon-agent/v1/schema.yaml` or tracked examples for the documented contract surface
- `tests` for executable confirmation that the contract still holds

## Bottom Line

If callers depend on `bijux-canon-agent` for orchestration behavior, the contract needs to be named as clearly as the implementation.
