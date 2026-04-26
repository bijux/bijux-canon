---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Foundation

The foundation section explains why the repository exists in this shape before
it explains how the root is operated.

Open this section when the repository still feels abstract. A reader should
leave it able to answer a small set of durable questions without guessing from
directory names: why the monorepo is split, where authority changes hands,
which names mean something stable, and what kind of change would damage that
clarity.

This is the place where the root becomes legible as a design boundary rather
than a pile of shared files. If these pages are healthy, later workflow and
review pages can assume the reader already understands what the repository is
trying to protect.

## Visual Summary

```mermaid
flowchart LR
    reader["reader question<br/>why is the repository split this way?"]
    split["repository split and package map"]
    boundary["ownership boundaries<br/>root versus package"]
    language["shared language and decision rules"]
    change["change principles<br/>what weakens clarity"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    class reader page;
    class split,boundary,language positive;
    class change caution;
    reader --> split
    reader --> boundary
    reader --> language
    reader --> change
```

## Start Here

- open [Platform Overview](platform-overview.md) for the shortest statement of
  what the repository is trying to protect
- open [Ownership Model](ownership-model.md) when the real question is where
  the root stops and a package begins
- open [Package Map](package-map.md) when you need the split rendered as owned
  roles instead of directory names
- open [Decision Rules](decision-rules.md) before making a cross-package change
  that might blur authority

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

- the monorepo shape is still more obvious than the monorepo intent
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

- open [Operations](../operations/index.md) when the question becomes how to
  run, validate, release, or review shared work
- open the owning product handbook when a boundary question resolves into one
  package's local behavior
- open [Maintainer Handbook](../../07-bijux-canon-maintain/index.md) when the
  issue is repository-health automation rather than repository intent

## Reader Takeaway

Use `Foundation` to make the split intelligible before touching workflow
detail. If a proposal makes the repository easier to use only by making the
ownership story blurrier, it is probably weakening the design rather than
improving it.

## Purpose

This page gives readers a clean starting point for the repository foundation
without forcing them to skim all of the topic pages first.
