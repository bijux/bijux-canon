---
title: Capability Map
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Capability Map

The capability map for `bijux-canon-ingest` should let a reviewer connect a package promise to the code that carries it. If a capability cannot be tied to a stable module area, it is not owned clearly enough yet.

## Capability To Code

- `processing/` owns cleaning, normalization, and chunking before retrieval begins
- `retrieval/` owns ingest-side record shaping and handoff-ready assembly
- `interfaces/` and `safeguards/` own the package surfaces that make ingest behavior repeatable and defensible

## Visible Outputs

- normalized source material
- chunk collections and retrieval-ready records
- ingest diagnostics that explain how preparation behaved

## Bottom Line

A capability is only real when a reviewer can trace it to code, tests, and outputs without guessing.
