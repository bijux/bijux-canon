---
title: Retirement Conditions
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Retirement Conditions

A compatibility package can be retired only when the dependent environments
that still need it are understood and the retirement path is documented.

Retirement is where honesty matters most. A package should not survive on
vague anxiety, and it should not disappear on untested optimism.

## Retirement Signals

- no remaining supported consumers depend on the legacy name
- migration guidance has been in place long enough to be credible
- removal will not silently strand existing automation

## Concrete Anchors

- `packages/compat-*` for the preserved legacy packages
- the compatibility package `README.md` files for canonical targets
- the matching canonical package docs for current behavior and new work

## Open This Page When

- you are tracing a legacy package name back to its canonical replacement
- you need migration guidance rather than product implementation detail
- you are deciding whether a compatibility surface still deserves to exist

## Decision Rule

Use this page when the main question is whether a compatibility package is
ready to retire. If evidence is still missing, keep the package temporarily and
close the gap instead of guessing.

## What You Can Resolve Here

- which retirement signals need to be verified
- when new work should open the canonical package instead
- what evidence would justify removing a compatibility package

## Review Focus

- compare legacy names here with the compatibility package metadata and README targets
- check that migration advice still points at current canonical docs
- confirm that compatibility language does not accidentally encourage new work to start here

## Read Next

- open the canonical package docs once the current target package is known:
  `https://bijux.io/bijux-canon/02-bijux-canon-ingest/`,
  `https://bijux.io/bijux-canon/03-bijux-canon-index/`,
  `https://bijux.io/bijux-canon/04-bijux-canon-reason/`,
  `https://bijux.io/bijux-canon/05-bijux-canon-agent/`, or
  `https://bijux.io/bijux-canon/06-bijux-canon-runtime/`
- inspect compatibility package metadata if the question is about what remains preserved
- open `https://bijux.io/bijux-canon/08-compat-packages/migration/dependency-continuity/`
  when the question turns back to why continuity still matters

## Limits

This section documents preserved legacy surfaces, but it does not claim those legacy names are the preferred place for new work or long-term design growth. If a legacy name remains, that is a migration fact, not a design endorsement.

