---
title: Schema Governance
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Schema Governance

`bijux-canon-dev` owns the repository helpers that keep API schemas and tracked
artifacts aligned with the code that claims to implement them. Schema drift is
one of the easiest ways to ship silent incompatibility, so the governance path
has to be inspectable.

## Governing Surfaces

- `api/openapi_drift.py` for schema drift detection
- `api/freeze_contracts.py` for tracked API artifact discipline
- tests such as `test_openapi_drift.py` and `test_api_freeze_contracts.py`
- checked-in artifacts under `apis/`

## Compatibility Threshold

A schema change stops being routine maintenance when the tracked artifact,
contract test, and consumer expectation no longer move together. At that point
the reviewer should treat it as a compatibility event, not as a formatting or
bookkeeping change.

## First Proof Check

- `packages/bijux-canon-dev/src/bijux_canon_dev/api`
- `packages/bijux-canon-dev/tests/test_openapi_drift.py`
- `packages/bijux-canon-dev/tests/test_api_freeze_contracts.py`
- tracked files under `apis/`

## Boundary

This page governs the repository checks around schemas. It does not replace the
package handbooks that explain what an API means or why a contract changed.
