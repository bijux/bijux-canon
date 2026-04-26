---
title: Dependency Direction
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Dependency Direction

Dependency direction matters because `bijux-canon-ingest` should make source preparation before retrieval begins easier to explain, not harder. Imported convenience must not reverse the ownership logic of the package.

## What To Check

- dependencies should point toward supporting source preparation before retrieval begins, not toward re-owning neighbor behavior
- upstream and downstream seams should stay legible across raw source material to prepared handoff output
- if the direction only makes sense after a long verbal explanation, the structure is already drifting

## First Proof Check

- `src/bijux_canon_ingest/processing`, `retrieval`, and `application` for the structural ownership boundary
- `tests` for deterministic preparation evidence for executable confirmation that the structure still holds

## Bottom Line

If `bijux-canon-ingest` needs hidden structure to defend source preparation before retrieval begins, the architecture is already too opaque.
