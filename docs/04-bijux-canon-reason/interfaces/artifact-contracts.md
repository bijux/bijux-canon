---
title: Artifact Contracts
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Artifact Contracts

Artifacts from `bijux-canon-reason` become contracts when another reader, tool, or package depends on their names, layout, or semantics. Visible output alone is not enough; the stable artifact story has to be explicit.

## What To Check

- name the durable artifacts behind claims, checks, provenance payloads, and reasoning artifacts
- separate reviewable artifacts from local debug residue or incidental output
- treat path, naming, or semantic drift as compatibility pressure when downstream readers rely on it

## First Proof Check

- `src` and boundary-facing modules for the owning implementation surface
- `apis/bijux-canon-reason/v1/schema.yaml` or tracked examples for the documented contract surface
- `tests` for executable confirmation that the contract still holds

## Bottom Line

If callers depend on `bijux-canon-reason` for reasoning output, the contract needs to be named as clearly as the implementation.
