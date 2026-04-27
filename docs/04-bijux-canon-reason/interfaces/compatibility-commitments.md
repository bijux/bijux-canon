---
title: Compatibility Commitments
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Compatibility Commitments

Compatibility commitments for `bijux-canon-reason` define how changes to reasoning output are supposed to be reviewed and announced. Stability language is only credible when the breakage process is explicit too.

## What To Check

- name which surfaces carry real compatibility pressure
- tie breaking changes to docs, changelog, versioning, and validation together
- treat vague stability claims as weaker than clear limits and explicit break rules

## First Proof Check

- `src` and boundary-facing modules for the owning implementation surface
- `apis/bijux-canon-reason/v1/schema.yaml` or tracked examples for the documented contract surface
- `tests` for executable confirmation that the contract still holds

## Bottom Line

If callers depend on `bijux-canon-reason` for reasoning output, the contract needs to be named as clearly as the implementation.
