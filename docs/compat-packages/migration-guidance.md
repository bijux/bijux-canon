---
title: Migration Guidance
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Migration Guidance

New work should target the canonical package names directly and treat the
compatibility packages as temporary bridges.

This page should make the path forward feel more concrete than the comfort of
staying on the legacy name. If readers leave unsure which name to use next,
the migration story is still too weak.

These compatibility pages should make legacy names understandable without romanticizing them. Their value is in helping readers migrate with less ambiguity, not in making the old names feel equally current.

## Visual Summary

```mermaid
flowchart RL
    page["Migration Guidance<br/>clarifies: map old names | choose migration | judge retirement"]
    classDef page fill:#dbeafe,stroke:#1d4ed8,color:#1e3a8a,stroke-width:2px;
    classDef positive fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef caution fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef anchor fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    classDef action fill:#fef3c7,stroke:#d97706,color:#7c2d12;
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
    pressure1["migration pressure"]
    pressure1 -.should shorten the life of.-> page
    pressure2["retirement readiness"]
    pressure2 -.should shorten the life of.-> page
    pressure3["do not normalize the old name"]
    pressure3 -.should shorten the life of.-> page
    class page page;
    class legacy1,legacy2,legacy3 caution;
    class canon1,canon2,canon3 positive;
    class pressure1,pressure2,pressure3 action;
```

## Recommended Migration Pattern

- switch dependencies to the canonical `bijux-canon-*` distribution
- switch imports to the canonical package docs and source roots
- keep compatibility packages only where an external environment still depends on them

## Concrete Anchors

- `packages/compat-*` for the preserved legacy packages
- the compatibility package `README.md` files for canonical targets
- the matching canonical package docs for current behavior and new work

## Use This Page When

- you are tracing a legacy package name back to its canonical replacement
- you need migration guidance rather than product implementation detail
- you are deciding whether a compatibility surface still deserves to exist

## Decision Rule

Use `Migration Guidance` to decide whether a preserved legacy name is still serving a real migration need. If the only reason to keep it is habit rather than an identified dependent environment, the section should bias the reviewer toward migration or retirement planning.

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

This page tells maintainers how to move away from legacy names without ambiguity.

## Stability

Keep it aligned with the canonical packages that compatibility packages currently point to.
