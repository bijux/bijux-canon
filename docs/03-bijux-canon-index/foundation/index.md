---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-26
---

# Foundation

`bijux-canon-index` exists to turn ingest-ready material into searchable,
replayable retrieval behavior. Use this section when the important question is
why retrieval ownership lives here and where it stops before reasoning or
runtime take over.

These pages should help readers separate three different concerns that often get
blurred together: ingest preparation, index execution, and reasoning over
retrieved results. When this section is clear, the package boundary is easier
to defend and easier to change responsibly.

## Visual Summary

```mermaid
flowchart LR
    ingest["prepared chunks and records"]
    embed["embedding and index execution"]
    retrieve["provenance-aware retrieval"]
    replay["replayable retrieval behavior"]
    boundary["boundary<br/>reasoning and orchestration start after retrieval"]
    reader["reader question<br/>why does index own this step?"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    class ingest,page reader;
    class embed,retrieve,replay positive;
    class boundary caution;
    ingest --> embed --> retrieve --> replay
    replay --> boundary
    replay --> reader
```

## Start Here

- open [Package Overview](package-overview.md) for the shortest explanation of
  what the index package is for
- open [Ownership Boundary](ownership-boundary.md) when retrieval behavior may
  be confused with ingest preparation or reasoning semantics
- open [Lifecycle Overview](lifecycle-overview.md) when the key question is how
  prepared material becomes a replayable retrieval surface

## Pages In This Section

- [Package Overview](package-overview.md)
- [Scope and Non-Goals](scope-and-non-goals.md)
- [Ownership Boundary](ownership-boundary.md)
- [Repository Fit](repository-fit.md)
- [Capability Map](capability-map.md)
- [Domain Language](domain-language.md)
- [Lifecycle Overview](lifecycle-overview.md)
- [Dependencies and Adjacencies](dependencies-and-adjacencies.md)
- [Change Principles](change-principles.md)

## Use This Section When

- you need the durable ownership story behind embeddings, retrieval, and replay
- you are deciding whether work belongs in index or in the packages before or
  after it
- you need shared package language for retrieval behavior before reading code or
  contracts

## Do Not Use This Section When

- the question is already about a command, schema, artifact, or import surface
- the real issue is operational, such as local setup, diagnostics, or release
- you already know the boundary and need proof, risks, or validation instead

## Read Across The Package

- open [Architecture](../architecture/index.md) when you need the structural
  map behind domain, application, and infrastructure flow
- open [Interfaces](../interfaces/index.md) when the question is about public
  retrieval contracts
- open [Operations](../operations/index.md) when you need setup, local
  workflows, or release guidance
- open [Quality](../quality/index.md) when you need evidence that replay and
  retrieval behavior are actually protected

## Concrete Anchors

- `packages/bijux-canon-index` as the package root
- `packages/bijux-canon-index/src/bijux_canon_index` as the import boundary
- `packages/bijux-canon-index/tests` as the proof surface for owned behavior

## Reader Takeaway

Use `Foundation` to answer the ownership question with integrity: index exists
to make retrieval behavior explicit, replayable, and dependable enough for
downstream packages to use. If a proposed change broadens the package without
making that retrieval story clearer, it is probably crossing a boundary rather
than improving the design.

## Purpose

This page introduces the foundation handbook for `bijux-canon-index` and routes
readers to the boundary, language, and lifecycle pages that explain why the
package exists.
