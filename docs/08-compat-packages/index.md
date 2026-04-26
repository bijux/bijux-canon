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
flowchart LR
    legacyDist["Legacy distribution<br/>name in requirements"]
    legacyImport["Legacy import<br/>name in code"]
    legacyCommand["Legacy command<br/>name in scripts"]
    compat["Compatibility packages<br/>preserve old entry names"]
    catalog["Catalog pages<br/>identify the exact target"]
    migration["Migration pages<br/>decide keep, migrate, or retire"]
    canon["Canonical packages<br/>carry current behavior"]
    newWork["New work starts here<br/>not in compatibility packages"]
    retire["Retirement review<br/>removes no-longer-needed bridges"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    legacyDist --> compat
    legacyImport --> compat
    legacyCommand --> compat
    compat --> catalog
    compat --> migration
    catalog --> canon
    migration --> canon
    canon --> newWork
    migration --> retire
    class compat page;
    class canon,newWork positive;
    class legacyDist,legacyImport,legacyCommand caution;
    class catalog,migration anchor;
    class retire action;
```

## Sections

- [Catalog](catalog/index.md) for legacy package entries, preserved names, and
  the concrete surfaces each compatibility package still carries
- [Migration](migration/index.md) for rename planning, dependency continuity,
  validation, release posture, and retirement decisions

## Pages In Catalog

- [agentic-flows](catalog/agentic-flows.md)
- [bijux-agent](catalog/bijux-agent.md)
- [bijux-rag](catalog/bijux-rag.md)
- [bijux-rar](catalog/bijux-rar.md)
- [bijux-vex](catalog/bijux-vex.md)
- [Legacy Name Map](catalog/legacy-name-map.md)
- [Package Behavior](catalog/package-behavior.md)
- [Import Surfaces](catalog/import-surfaces.md)
- [Command Surfaces](catalog/command-surfaces.md)

## Pages In Migration

- [Compatibility Overview](migration/compatibility-overview.md)
- [Migration Guidance](migration/migration-guidance.md)
- [Repository Consolidation](migration/repository-consolidation.md)
- [Canonical Targets](migration/canonical-targets.md)
- [Dependency Continuity](migration/dependency-continuity.md)
- [Release Policy](migration/release-policy.md)
- [Validation Strategy](migration/validation-strategy.md)
- [Retirement Conditions](migration/retirement-conditions.md)
- [Retirement Playbook](migration/retirement-playbook.md)

## Retired Standalone Repositories

- `https://github.com/bijux/agentic-flows`
- `https://github.com/bijux/bijux-agent`
- `https://github.com/bijux/bijux-rag`
- `https://github.com/bijux/bijux-rar`
- `https://github.com/bijux/bijux-vex`

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
