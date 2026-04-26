---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Foundation

The foundation section explains why the repository is split this way before it
explains how the root is operated. These pages define the design boundary that
keeps package ownership explicit: why the monorepo exists, where authority
changes hands, which terms stay stable, and which changes would weaken that
clarity.

## Visual Summary

```mermaid
flowchart LR
    split["repository split<br/>why these packages exist separately"]
    scope["repository scope<br/>what the root can and cannot own"]
    map["package map<br/>where authority changes hands"]
    language["domain language<br/>shared terms with stable meaning"]
    rules["decision rules<br/>changes that preserve or blur clarity"]
    split --> scope --> map --> language --> rules
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    class split,scope,map,language positive;
    class rules caution;
```

## Start Here

- open [Platform Overview](platform-overview.md) for the shortest statement of the repository design
- open [Repository Scope](repository-scope.md) when the question is what the root may document, enforce, or coordinate
- open [Ownership Model](ownership-model.md) when the concern is where the root stops and a package begins
- open [Package Map](package-map.md) when the split needs to be read as owned responsibilities instead of directory names
- open [Decision Rules](decision-rules.md) before making a cross-package change that might blur authority

## Pages in This Section

- [Platform Overview](platform-overview.md)
- [Repository Scope](repository-scope.md)
- [Workspace Layout](workspace-layout.md)
- [Package Map](package-map.md)
- [Ownership Model](ownership-model.md)
- [Domain Language](domain-language.md)
- [Documentation System](documentation-system.md)
- [Change Principles](change-principles.md)
- [Decision Rules](decision-rules.md)

## Use This Section When

- the monorepo shape is still clearer than the monorepo intent
- you need to decide whether work belongs at the root or in a package
- you want the shortest route to the repository's enduring design logic

## Do Not Use This Section When

- the real question is already about validation commands, release flow, or
  shared automation
- you need one package's interfaces, workflows, or tests instead of root logic
- you are already in maintainer-only workflow territory

## Concrete Anchors

- `pyproject.toml` for the declared workspace boundary
- `packages/` for the product split this section explains
- [Package Map](package-map.md) and [Ownership Model](ownership-model.md) for
  the clearest statement of authority changes
- [Decision Rules](decision-rules.md) for the root-level test of whether a
  proposed change strengthens or blurs the split

## Read Across The Repository

- open [Operations](../operations/index.md) when the question becomes how to run, validate, release, or review shared work
- open the owning product handbook when a boundary question resolves into one package's local behavior
- open [Maintainer Handbook](../../07-bijux-canon-maintain/index.md) when the issue is repository-health automation rather than repository intent

## Design Pressure

The split should remain easier to defend after a change than before it. If a
proposal simplifies one local task only by making ownership boundaries harder
to explain, the proposal is weakening the repository even if it reduces
short-term friction.
