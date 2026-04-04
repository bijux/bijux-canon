---
title: Compatibility Packages
audience: mixed
type: index
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-04
---

# Compatibility Packages

The compatibility packages preserve older distribution names, import names,
and command names while the canonical package family now lives under the
`bijux-canon-*` naming system.

They should be easy to understand but hard to romanticize. Their job is to
reduce migration pain, not to compete with the canonical package family for
new work.

These compatibility pages should make legacy names understandable without romanticizing them. Their value is in helping readers migrate with less ambiguity, not in making the old names feel equally current.

## Visual Summary

```mermaid
flowchart RL
    page["Compatibility Packages<br/>clarifies: map old names | choose migration | judge retirement"]
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
    canon1["current handbook surfaces"]
    page --> canon1
    canon2["current packages"]
    page --> canon2
    canon3["new work"]
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

## Pages in This Section

- [Compatibility Overview](compatibility-overview.md)
- [Legacy Name Map](legacy-name-map.md)
- [Migration Guidance](migration-guidance.md)
- [Package Behavior](package-behavior.md)
- [Import Surfaces](import-surfaces.md)
- [Command Surfaces](command-surfaces.md)
- [Release Policy](release-policy.md)
- [Validation Strategy](validation-strategy.md)
- [Retirement Conditions](retirement-conditions.md)

## Legacy Name Map

- `agentic-flows` maps to `bijux-canon-runtime`
- `bijux-agent` maps to `bijux-canon-agent`
- `bijux-rag` maps to `bijux-canon-ingest`
- `bijux-rar` maps to `bijux-canon-reason`
- `bijux-vex` maps to `bijux-canon-index`

## Concrete Anchors

- `packages/compat-*` for the preserved legacy packages
- the compatibility package `README.md` files for canonical targets
- the matching canonical package docs for current behavior and new work

## Use This Page When

- you are tracing a legacy package name back to its canonical replacement
- you need migration guidance rather than product implementation detail
- you are deciding whether a compatibility surface still deserves to exist

## Decision Rule

Use `Compatibility Packages` to decide whether a preserved legacy name is still serving a real migration need. If the only reason to keep it is habit rather than an identified dependent environment, the section should bias the reviewer toward migration or retirement planning.

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

This page explains the role of the compatibility handbooks without encouraging new work to start there.

## Stability

Keep it aligned with the legacy packages that still ship from `packages/compat-*`.
