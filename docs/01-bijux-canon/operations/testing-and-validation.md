---
title: Testing and Validation
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Testing and Validation

Validation in `bijux-canon` is layered: packages protect their own behavior,
while the repository protects the seams between packages, schemas, docs, and
release conventions.

## Validation Order

1. run package-local proof first when the behavior is owned by one package
2. run shared root checks when the change reaches schemas, docs, workflows, or
   release governance
3. confirm that the documentation claim and the executable proof still match

## Shared Validation Surfaces

- package-local unit, integration, e2e, and invariant suites
- schema drift and packaging checks in `bijux-canon-dev`
- repository CI workflows under `.github/workflows/`

## Most Important Failure

The highest-cost validation mistake is letting a shared prose promise survive
without a test, workflow, or schema check that can notice drift. At that point
the repository is asking readers to trust style instead of proof.

## First Proof Checks

- the owning package tests when the change is still local
- `.github/workflows/` and maintainer tooling when the rule crosses packages
- `apis/` when the claim is about tracked contract alignment

## Bottom Line

Trust is local before it is global. Each package proves its own promises first,
then the repository proves the packages still fit together honestly.
