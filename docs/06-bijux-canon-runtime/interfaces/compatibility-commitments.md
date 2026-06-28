---
title: Compatibility Commitments
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Compatibility Commitments

Compatibility commitments for `bijux-canon-runtime` define how changes to
runtime authority surfaces are supposed to be reviewed and announced. Stability
language is only credible when the breakage process is explicit too.

Runtime compatibility here includes more than one old repository name. The
canonical runtime package still preserves two direct continuity distributions:
`agentic-flows` for the retired standalone runtime identity and `bijux-canon`
for the shorter family-root runtime identity. Both are real alias packages that
must resolve to the same runtime behavior, not migration-only stubs.

## What To Check

- name which surfaces carry real compatibility pressure
- tie breaking changes to docs, changelog, versioning, and validation together
- treat vague stability claims as weaker than clear limits and explicit break rules

## Runtime Alias Surfaces

- preserved distributions: `bijux-canon`, `agentic-flows`
- preserved import roots: `bijux_canon`, `agentic_flows`
- preserved commands: `bijux-canon`, `agentic-flows`
- canonical authority surface: `bijux-canon-runtime`

If one of those preserved names stops behaving like the canonical runtime
surface, the break is not cosmetic. It is a runtime compatibility regression.

## Review Rule

- change runtime alias behavior only when the canonical runtime package, alias
  package README files, compatibility handbook pages, and release notes move
  together
- prefer executable alias parity checks over prose-only claims
- reject changes that leave compatibility names installable but behaviorally
  different from the canonical runtime package without an explicit break
  decision

## First Proof Check

- `src` and boundary-facing modules for the owning implementation surface
- `packages/compat-bijux-canon` and `packages/compat-agentic-flows` for the
  preserved alias package contract
- `apis/bijux-canon-runtime/v1/schema.yaml` or tracked examples for the documented contract surface
- `tests` for executable confirmation that the contract still holds

## Bottom Line

If callers depend on `bijux-canon-runtime` through either the canonical name or
its preserved alias names, the contract needs to be named as clearly as the
implementation.
