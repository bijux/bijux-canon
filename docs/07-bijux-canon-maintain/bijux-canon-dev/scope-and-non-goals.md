---
title: Scope and Non-Goals
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Scope and Non-Goals

`bijux-canon-dev` exists for maintainer-only work that protects repository
health across packages. It should stay narrow enough that a reviewer can still
see where maintainer infrastructure ends and product behavior begins.

## In Scope

- repository-wide quality, security, release, docs, and SBOM helpers
- schema and API contract checks that compare code with checked-in artifacts
- package-specific maintenance adapters that support shared repository rules

## Out Of Scope

- end-user runtime behavior in canonical packages
- package-local domain models that do not serve repository health
- compatibility bridges for legacy distribution, import, or command names

## Borderline Cases

A change belongs here only when the rule is shared and the integration point is
explicit. If the rule mainly explains one package's behavior, document and
implement it in that package even if the maintainer package can technically call
it.

## First Proof Check

- helper modules under `src/bijux_canon_dev/`
- tests under `packages/bijux-canon-dev/tests`
- consumers in `apis/`, `makes/`, and `.github/workflows/`
