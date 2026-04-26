---
title: Validation Strategy
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Validation Strategy

Compatibility packages are small, but they still need validation for import
preservation, packaging metadata, and migration pointers.

Small does not mean unimportant. These packages carry trust mainly through
naming continuity, so the validation has to prove that the bridge still
points to the right place.

These compatibility pages should make legacy names understandable without romanticizing them. Their value is in helping readers migrate with less ambiguity, not in making the old names feel equally current.

## Visual Summary

```mermaid
flowchart RL
    page["Validation Strategy<br/>clarifies: map old names | choose migration | judge retirement"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    legacy1["command names"]
    legacy1 --> page
    legacy2["distribution names"]
    legacy2 --> page
    legacy3["import names"]
    legacy3 --> page
    canon1["new work"]
    page --> canon1
    canon2["current handbook surfaces"]
    page --> canon2
    canon3["current packages"]
    page --> canon3
    pressure1["do not normalize the old name"]
    pressure1 -.should shorten the life of.-> page
    pressure2["migration pressure"]
    pressure2 -.should shorten the life of.-> page
    pressure3["retirement readiness"]
    pressure3 -.should shorten the life of.-> page
    class page page;
    class legacy1,legacy2,legacy3 caution;
    class canon1,canon2,canon3 positive;
    class pressure1,pressure2,pressure3 action;
```

## Validation Focus

- import resolution
- packaging metadata correctness
- links and references to the canonical package docs

## Concrete Anchors

- `packages/compat-*` for the preserved legacy packages
- the compatibility package `README.md` files for canonical targets
- the matching canonical package docs for current behavior and new work

## Use This Page When

- you are tracing a legacy package name back to its canonical replacement
- you need migration guidance rather than product implementation detail
- you are deciding whether a compatibility surface still deserves to exist

## Decision Rule

Use `Validation Strategy` to decide whether a preserved legacy name is still serving a real migration need. If the only reason to keep it is habit rather than an identified dependent environment, the section should bias the reviewer toward migration or retirement planning.

## What This Page Answers

- which legacy surface is still preserved
- when new work should move to the canonical package instead
- what evidence would justify retiring a compatibility package

## Reviewer Lens

- compare legacy names here with the compatibility package metadata and README targets
- check that migration advice still points at current canonical docs
- confirm that compatibility language does not accidentally encourage new work to start here

## Next Checks

- move to the canonical package docs once the current target package is known
- inspect compatibility package metadata if the question is about what remains preserved
- use this section again only when evaluating migration progress or retirement readiness

## Honesty Boundary

This section documents preserved legacy surfaces, but it does not claim those legacy names are the preferred place for new work or long-term design growth. If a legacy name remains, that is a migration fact, not a design endorsement.

## Purpose

This page explains what counts as sufficient validation for the compatibility layer.

## Stability

Keep it aligned with the actual compatibility package tests or maintenance checks.
