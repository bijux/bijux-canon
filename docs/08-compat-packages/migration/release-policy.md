---
title: Release Policy
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Release Policy

Compatibility packages should release only when they still serve a real
migration need or when the canonical target package changes in a way that
requires compatibility metadata to move with it.

A compatibility release should feel justified, narrow, and temporary. If the
release story starts sounding like ordinary feature delivery, the layer is
drifting away from its purpose.

These compatibility pages make legacy names understandable without romanticizing them. Their value is in helping readers migrate with less ambiguity, not in making the old names feel equally current.

## Policy

- keep releases narrow and clearly justified
- avoid feature growth inside the compatibility packages
- document canonical targets in every compatibility package README

## Concrete Anchors

- `packages/compat-*` for the preserved legacy packages
- the compatibility package `README.md` files for canonical targets
- the matching canonical package docs for current behavior and new work

## Open This Page When

- you are tracing a legacy package name back to its canonical replacement
- you need migration guidance rather than product implementation detail
- you are deciding whether a compatibility surface still deserves to exist

## Decision Rule

Use `Release Policy` to decide whether a preserved legacy name is still serving a real migration need. If the only reason to keep it is habit rather than an identified dependent environment, the section should bias the reviewer toward migration or retirement planning.

## What You Can Resolve Here

- which legacy surface is still preserved
- when new work should open the canonical package instead
- what evidence would justify retiring a compatibility package

## Review Focus

- compare legacy names here with the compatibility package metadata and README targets
- check that migration advice still points at current canonical docs
- confirm that compatibility language does not accidentally encourage new work to start here

## Read Next

- open the canonical package docs once the current target package is known
- inspect compatibility package metadata if the question is about what remains preserved
- use this section again only when evaluating migration progress or retirement readiness

## Limits

This section documents preserved legacy surfaces, but it does not claim those legacy names are the preferred place for new work or long-term design growth. If a legacy name remains, that is a migration fact, not a design endorsement.

