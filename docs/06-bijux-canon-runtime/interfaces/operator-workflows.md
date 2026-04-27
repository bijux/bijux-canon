---
title: Operator Workflows
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Operator Workflows

Operator workflows matter when `bijux-canon-runtime` is run by humans or automation under real expectations. The workflow should show one supported operator path from entrypoint to reviewable output.

## What To Check

- name the supported operator path rather than every possible internal path
- identify the output or artifact the operator should inspect at the end
- treat undocumented manual steps as evidence that the workflow is not yet a real surface

## First Proof Check

- `src` and boundary-facing modules for the owning implementation surface
- `apis/bijux-canon-runtime/v1/schema.yaml` or tracked examples for the documented contract surface
- `tests` for executable confirmation that the contract still holds

## Bottom Line

If callers depend on `bijux-canon-runtime` for runtime authority surfaces, the contract needs to be named as clearly as the implementation.
