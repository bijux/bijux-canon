---
title: Capability Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Capability Map

The capability map for `bijux-canon-index` should let a reviewer trace retrieval promises back to the modules that execute, compare, and expose search behavior. If a retrieval promise has no visible home, the package contract is weaker than it looks.

## Capability To Code

- `application/` and package workflows coordinate search execution at the package seam
- `domain/`, backend modules, and retrieval services own embedding, retrieval, and comparison behavior
- `interfaces/` and `apis/` own the surfaces that callers depend on when retrieval becomes a contract

## Visible Outputs

- embeddings and index state tied to prepared input
- retrieval results with provenance and replay context
- caller-facing search artifacts and schemas

## Bottom Line

A capability is only real when a reviewer can trace it to code, tests, and outputs without guessing.
