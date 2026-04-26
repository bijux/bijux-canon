---
title: Command Surfaces
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Command Surfaces

Some compatibility packages also preserve historic command names so migration
does not break operator scripts immediately.

A preserved command is a safety rail on the way to the canonical package, not a
new invitation to stay on the old name forever.

## Command Rule

A compatibility command should only exist when the canonical package still
provides a meaningful route behind it.

## Concrete Anchors

- `packages/compat-*` for the preserved legacy packages
- the compatibility package `README.md` files for canonical targets
- the matching canonical package docs for current behavior and new work

## Open This Page When

- you are tracing a legacy package name back to its canonical replacement
- you need migration guidance rather than product implementation detail
- you are deciding whether a compatibility surface still deserves to exist

## Decision Rule

Use this page when the main question is whether a preserved command still
serves a real migration need. If the only reason to keep it is habit rather
than an identified dependent environment, plan migration or retirement instead.

## What You Can Resolve Here

- which legacy commands are still preserved
- which canonical CLIs replace them
- what evidence would justify retiring a compatibility command surface

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
- continue to `https://bijux.io/bijux-canon/08-compat-packages/migration/retirement-conditions/`
  when the question turns into retirement readiness

## Limits

This section documents preserved legacy surfaces, but it does not claim those legacy names are the preferred place for new work or long-term design growth. If a legacy name remains, that is a migration fact, not a design endorsement.

