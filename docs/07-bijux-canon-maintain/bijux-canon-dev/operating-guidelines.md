---
title: Operating Guidelines
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Operating Guidelines

Changes in `bijux-canon-dev` deserve extra caution because they can affect many
packages at once. The right posture is explicit scope, explicit proof, and
explicit package impact.

## Working Rules

- prefer checked-in helper code and tests over opaque shell glue
- keep package impact visible whenever a shared rule fans out across the matrix
- state the owning integration point when a helper is consumed by `make` or a
  workflow
- keep maintainer-only guidance here instead of leaking it into product pages

## Review Questions

- does this helper protect a repository-wide rule or a package-local behavior
- can a reviewer trace the rule from helper module to test to caller
- would a product package handbook be the more honest place to explain the
  behavior

## First Proof Check

- helper modules under `src/bijux_canon_dev/`
- tests under `packages/bijux-canon-dev/tests`
- callers in `makes/`, `.github/workflows/`, and `apis/`
