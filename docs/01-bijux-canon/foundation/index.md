---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Foundation

The foundation section explains the design boundary that keeps package
ownership explicit: why the repository exists, where authority changes hands,
which terms stay stable, and which changes would weaken that clarity.

The main mistake this section should prevent is treating the root as a
convenient overflow area. These pages exist so a reviewer can tell, early and
plainly, whether a change belongs in shared governance or in one owning
package.

## Foundation Map

Foundation pages should make the repository's authority model visible before a
reader gets lost in package detail. The root explains why the split exists,
where the shared workspace boundary sits, and which decision rules protect the
package family from slow boundary drift.

```mermaid
flowchart LR
    intent["platform intent"]
    scope["repository scope"]
    layout["workspace layout"]
    packages["package map"]
    language["domain language"]
    decisions["decision rules"]
    package["owning package handbook"]
    blur["root creep"]

    intent --> scope --> layout --> packages --> language --> decisions
    scope --> package
    decisions --> blur
```

Foundation pages should help a reviewer defend the split out loud. They are not
there to decorate the repository with theory. They exist to answer why the
root owns anything at all, where that authority stops, and which terms or rules
must stay stable if package boundaries are going to remain believable.

## Start Here

- open [Platform Overview](https://bijux.io/bijux-canon/01-bijux-canon/foundation/platform-overview/) for the shortest statement of the repository design
- open [Repository Scope](https://bijux.io/bijux-canon/01-bijux-canon/foundation/repository-scope/) when you need to know what the root may document, enforce, or coordinate
- open [Ownership Model](https://bijux.io/bijux-canon/01-bijux-canon/foundation/ownership-model/) when you need the line between the root and a package
- open [Package Map](https://bijux.io/bijux-canon/01-bijux-canon/foundation/package-map/) when you want to read the split as owned responsibilities instead of directory names
- open [Decision Rules](https://bijux.io/bijux-canon/01-bijux-canon/foundation/decision-rules/) before making a cross-package change that might blur authority

## Pages In This Section

- [Platform Overview](https://bijux.io/bijux-canon/01-bijux-canon/foundation/platform-overview/)
- [Repository Scope](https://bijux.io/bijux-canon/01-bijux-canon/foundation/repository-scope/)
- [Workspace Layout](https://bijux.io/bijux-canon/01-bijux-canon/foundation/workspace-layout/)
- [Package Map](https://bijux.io/bijux-canon/01-bijux-canon/foundation/package-map/)
- [Ownership Model](https://bijux.io/bijux-canon/01-bijux-canon/foundation/ownership-model/)
- [Domain Language](https://bijux.io/bijux-canon/01-bijux-canon/foundation/domain-language/)
- [Documentation System](https://bijux.io/bijux-canon/01-bijux-canon/foundation/documentation-system/)
- [Change Principles](https://bijux.io/bijux-canon/01-bijux-canon/foundation/change-principles/)
- [Decision Rules](https://bijux.io/bijux-canon/01-bijux-canon/foundation/decision-rules/)

## Concrete Anchors

- `packages/` for the first ownership check when root scope feels arguable
- `pyproject.toml` for the declared workspace boundary
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

## Leave This Section When

- the question has narrowed to one package contract, workflow, or proof surface
- the concern is operational enforcement rather than repository intent
- the issue lives in maintainer-only automation instead of root-owned design logic
