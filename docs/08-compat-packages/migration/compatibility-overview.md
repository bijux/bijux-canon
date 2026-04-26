---
title: Compatibility Overview
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Compatibility Overview

These packages exist to reduce migration breakage, not to become the preferred
long-term entrypoints for new work.

The compatibility layer is a bridge with a cost. Preserving old names is
sometimes necessary, but it is still a debt that should stay visible and
justified.

## Visual Summary

```mermaid
flowchart TB
    legacy["Existing environments<br/>still use legacy names"]
    compat["Compatibility packages<br/>preserve those names"]
    canon["Canonical packages<br/>remain the current destination"]
    newWork["New development<br/>goes directly to canonical packages"]
    cost["Every preserved alias<br/>adds maintenance debt"]
    review["Review whether the bridge<br/>still serves a supported need"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    legacy --> compat
    compat --> canon
    newWork --> canon
    compat --> cost
    cost --> review
    canon --> review
    class compat page;
    class canon,newWork positive;
    class legacy caution;
    class cost,review action;
```

## Preserved Surfaces

- legacy distribution names
- legacy Python import names
- legacy command names where they still exist

## Concrete Anchors

- `packages/compat-*` for the preserved legacy packages
- the compatibility package `README.md` files for canonical targets
- the matching canonical package docs for current behavior and new work

## Use This Page When

- you are tracing a legacy package name back to its canonical replacement
- you need migration guidance rather than product implementation detail
- you are deciding whether a compatibility surface still deserves to exist

## Decision Rule

Use this page when the main question is whether a preserved legacy name still
serves a real migration need. If the only reason to keep it is habit rather
than an identified dependent environment, plan migration or retirement instead.

## What This Page Answers

- which legacy surfaces are still preserved
- when new work should move to the canonical packages instead
- what evidence would justify retiring a compatibility package

## Reviewer Lens

- compare legacy names here with the compatibility package metadata and README targets
- check that migration advice still points at current canonical docs
- confirm that compatibility language does not accidentally encourage new work to start here

## Next Checks

- move to the canonical package docs once the current target package is known:
  `https://bijux.io/bijux-canon/02-bijux-canon-ingest/`,
  `https://bijux.io/bijux-canon/03-bijux-canon-index/`,
  `https://bijux.io/bijux-canon/04-bijux-canon-reason/`,
  `https://bijux.io/bijux-canon/05-bijux-canon-agent/`, or
  `https://bijux.io/bijux-canon/06-bijux-canon-runtime/`
- inspect compatibility package metadata if the question is about what remains preserved
- continue to `https://bijux.io/bijux-canon/08-compat-packages/migration/validation-strategy/`
  for evidence behind the bridge

## Honesty Boundary

This section documents preserved legacy surfaces, but it does not claim those legacy names are the preferred place for new work or long-term design growth. If a legacy name remains, that is a migration fact, not a design endorsement.

## Purpose

This page gives the shortest description of why the compatibility packages
remain.

## Stability

Keep it aligned with the actual compatibility promises that are still checked in.
