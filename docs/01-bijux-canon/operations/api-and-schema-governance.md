---
title: API and Schema Governance
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# API and Schema Governance

Shared API artifacts live under `apis/` so schema review does not depend on
reading package source alone.

This page exists to answer one operational question clearly: when is a schema
change just local code movement, and when is it a compatibility event that
needs shared review.

## Compatibility Threshold

Treat a change as a shared compatibility event when it changes any caller- or
reader-facing contract that is tracked outside one module alone, including:

- request or response shapes in tracked OpenAPI material
- pinned schema artifacts under `apis/`
- field names, required fields, or semantics that more than one package or
  external caller depends on
- workflow checks whose purpose is to prove schema alignment

## First Proof Checks

- `apis/` for the tracked schema roots and pinned artifacts
- the owning package interface docs for the public contract being changed
- drift or validation checks under `.github/workflows/` and maintainer tooling
  when the change claims to stay safe

## Shared Schema Roots

- `apis/bijux-canon-agent/v1`
- `apis/bijux-canon-index/v1`
- `apis/bijux-canon-ingest/v1`
- `apis/bijux-canon-reason/v1`
- `apis/bijux-canon-runtime/v1`

## Bottom Line

A schema change stops being ordinary maintenance as soon as a caller, another
package, or a shared check would read it differently. At that point the change
needs explicit compatibility review, not just code review.
