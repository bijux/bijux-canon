---
title: makes
audience: mixed
type: index
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# makes

The `makes/` section explains the shared Make surface that ties repository
operations together.

The make system is a real interface in this repository. It is how local work,
CI checks, package dispatch, and release-oriented automation are exposed in a
repeatable way. These pages should help a maintainer see the structure behind
those targets instead of treating the make layer as a flat bag of commands.

```mermaid
flowchart LR
    root["root entrypoints"]
    env["environment model"]
    dispatch["package dispatch"]
    ci["CI targets"]
    release["release surfaces"]
    reader["reader question<br/>which make surface should I touch?"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    class root,page reader;
    class env,dispatch,ci,release positive;
    root --> reader
    env --> reader
    dispatch --> reader
    ci --> reader
    release --> reader
```

## Pages in This Section

- [Make System Overview](make-system-overview.md)
- [Root Entrypoints](root-entrypoints.md)
- [Environment Model](environment-model.md)
- [Repository Layout](repository-layout.md)
- [Package Dispatch](package-dispatch.md)
- [CI Targets](ci-targets.md)
- [Package Contracts](package-contracts.md)
- [Release Surfaces](release-surfaces.md)
- [Authoring Rules](authoring-rules.md)

## Use This Section When

- the concern is about shared Make entrypoints rather than package code itself
- you need to understand how local commands, CI targets, and release commands
  are routed
- you are editing the repository command surface that other maintainers depend
  on

## Do Not Use This Section When

- the question is about GitHub Actions trigger logic instead of Make routing
- the issue belongs to a product package contract rather than a shared command
  layer
- you only need one concrete target and already know which page documents it

## Choose The Next Page By Question

- open [Make System Overview](make-system-overview.md) for the broad structure
  first
- open [Root Entrypoints](root-entrypoints.md) when the concern starts at the
  top-level command surface
- open [Package Dispatch](package-dispatch.md) when the question is how shared
  targets route into one package or many
- open [CI Targets](ci-targets.md) or [Release Surfaces](release-surfaces.md)
  when the concern is automation-facing rather than developer-facing

## Purpose

This page routes maintainers into the make-system documentation without forcing
them to infer the structure from file names alone.

## Stability

Keep it aligned with the actual make surfaces the repository expects people and
automation to use.
