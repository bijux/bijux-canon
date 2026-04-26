---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Foundation

Use the foundation section to understand why the repository is split this way
before you move into operational detail. These pages define the design
boundary that keeps package ownership explicit: why the repository exists,
where authority changes hands, which terms stay stable, and which changes
would weaken that clarity.

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

- open [Platform Overview](https://bijux.io/bijux-canon/01-bijux-canon/foundation/platform-overview/) for the shortest statement of the repository design
- open [Repository Scope](https://bijux.io/bijux-canon/01-bijux-canon/foundation/repository-scope/) when you need to know what the root may document, enforce, or coordinate
- open [Ownership Model](https://bijux.io/bijux-canon/01-bijux-canon/foundation/ownership-model/) when you need the line between the root and a package
- open [Package Map](https://bijux.io/bijux-canon/01-bijux-canon/foundation/package-map/) when you want to read the split as owned responsibilities instead of directory names
- open [Decision Rules](https://bijux.io/bijux-canon/01-bijux-canon/foundation/decision-rules/) before making a cross-package change that might blur authority

## Pages In Foundation

- [Platform Overview](https://bijux.io/bijux-canon/01-bijux-canon/foundation/platform-overview/)
- [Repository Scope](https://bijux.io/bijux-canon/01-bijux-canon/foundation/repository-scope/)
- [Workspace Layout](https://bijux.io/bijux-canon/01-bijux-canon/foundation/workspace-layout/)
- [Package Map](https://bijux.io/bijux-canon/01-bijux-canon/foundation/package-map/)
- [Ownership Model](https://bijux.io/bijux-canon/01-bijux-canon/foundation/ownership-model/)
- [Domain Language](https://bijux.io/bijux-canon/01-bijux-canon/foundation/domain-language/)
- [Documentation System](https://bijux.io/bijux-canon/01-bijux-canon/foundation/documentation-system/)
- [Change Principles](https://bijux.io/bijux-canon/01-bijux-canon/foundation/change-principles/)
- [Decision Rules](https://bijux.io/bijux-canon/01-bijux-canon/foundation/decision-rules/)

## Open Foundation When

- you can see the repository shape but still need the design reason behind it
- you need to decide whether work belongs at the root or in a package
- you want the shortest route to the repository's enduring design logic

## Open Another Section When

- the real question is already about validation commands, release flow, or
  shared automation
- you need one package's interfaces, workflows, or tests instead of root logic
- you are already in maintainer-only workflow territory

## Concrete Anchors

- `pyproject.toml` for the declared workspace boundary
- `packages/` for the product split described in these pages
- [Package Map](https://bijux.io/bijux-canon/01-bijux-canon/foundation/package-map/) and [Ownership Model](https://bijux.io/bijux-canon/01-bijux-canon/foundation/ownership-model/) for
  the clearest statement of authority changes
- [Decision Rules](https://bijux.io/bijux-canon/01-bijux-canon/foundation/decision-rules/) for the root-level test of whether a
  proposed change strengthens or blurs the split

## Read Across The Repository

- open [Operations](https://bijux.io/bijux-canon/01-bijux-canon/operations/) when you need to run, validate, release, or review shared work
- open the owning product handbook when a boundary question resolves into one package's local behavior
- open the [Maintainer Handbook](https://bijux.io/bijux-canon/07-bijux-canon-maintain/) when the issue is repository-health automation rather than repository intent

## Design Pressure

The split should remain easier to defend after a change than before it. If a
proposal simplifies one local task only by making ownership boundaries harder
to explain, the proposal is weakening the repository even if it reduces
short-term friction.
