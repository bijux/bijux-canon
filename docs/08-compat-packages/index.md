---
title: Compatibility Packages
audience: mixed
type: index
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# Compatibility Packages

The compatibility packages preserve older distribution names, import names,
and command names while the canonical package family now lives under the
`bijux-canon-*` naming system.

Their job is migration continuity, not long-term product growth. A preserved
legacy name is a bridge to a canonical package, not an equal design center.

## Visual Summary

```mermaid
flowchart TB
    legacyDist["legacy distribution<br/>name in requirements"]
    legacyImport["legacy import<br/>name in code"]
    legacyCommand["legacy command<br/>name in scripts"]
    compat["compatibility package<br/>preserved entry surface"]
    catalog["catalog<br/>exact legacy-to-canonical mapping"]
    migration["migration<br/>continuity, validation, retirement"]
    canon["canonical package<br/>current owned behavior"]
    retire["retirement review<br/>remove bridge when dependency ends"]
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
    migration --> retire
    class compat page;
    class canon positive;
    class legacyDist,legacyImport,legacyCommand caution;
    class catalog,migration anchor;
    class retire action;
```

## Sections

- [Catalog](catalog/index.md) for legacy package entries, preserved names, and
  the concrete surfaces each compatibility package still carries
- [Migration](migration/index.md) for rename planning, dependency continuity,
  validation, release posture, and retirement decisions

## Use This Section When

- you started from a legacy package, import, or command name and need to find
  the current canonical target
- you are checking whether a compatibility surface still serves a real
  migration need
- you need migration or retirement guidance rather than product implementation

## Do Not Start Here When

- you already know the canonical package name and need current behavior docs
- you are designing new product behavior or a new public contract
- the question is about maintainer automation rather than compatibility

## Choose The Next Section By Question

- open [Catalog](catalog/index.md) when the immediate need is to identify which
  exact legacy surface is still preserved
- open [Migration](migration/index.md) when the immediate need is to plan
  dependency continuity, validation, or retirement
- move to the owning canonical package handbook once the current target package
  is known and the question becomes product behavior rather than migration

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

## Migration Rule

Preserving a legacy name is justified only when it protects an identified
dependent environment or lowers a real migration risk. Habit alone is not a
durable reason to keep compatibility packages shipping indefinitely.

## Compatibility Standard

Each compatibility page should make the exit route obvious: the preserved name,
the canonical target, the validation posture that protects the transition, and
the evidence required before the bridge can be retired.
