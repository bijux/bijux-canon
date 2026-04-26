---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-04-26
---

# Foundation

`bijux-canon-ingest` exists to turn raw source material into deterministic,
retrieval-ready output. Use this section when the important question is not
which command to run, but why ingest owns this work at all and where that
ownership stops.

These pages should help readers distinguish source preparation from the
downstream jobs that index, reason over, or orchestrate the prepared output.
When this section is doing its job well, a scientist, developer, or maintainer
can explain why ingest exists without falling back to repository tribal memory.

## Visual Summary

```mermaid
flowchart LR
    source["raw documents and records"]
    prepare["deterministic preparation"]
    chunk["chunking and record shaping"]
    handoff["retrieval-ready handoff"]
    boundary["boundary<br/>reasoning and runtime start later"]
    reader["reader question<br/>why does ingest own this step?"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    class source,page reader;
    class prepare,chunk,handoff positive;
    class boundary caution;
    source --> prepare --> chunk --> handoff
    handoff --> boundary
    handoff --> reader
```

## Start Here

- open [Package Overview](package-overview.md) for the shortest explanation of
  what ingest is for
- open [Ownership Boundary](ownership-boundary.md) when the issue might belong
  in index, reason, agent, or runtime instead
- open [Lifecycle Overview](lifecycle-overview.md) when the real question is
  how source material moves through ingest before downstream packages pick it up

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

- you need the durable ownership story before reading code or command docs
- you are deciding whether deterministic preparation belongs in ingest or
  downstream retrieval behavior belongs elsewhere
- you need shared package language for chunking, source shaping, and handoff

## Do Not Use This Section When

- the question is already about public commands, schemas, or artifact contracts
- the real problem is operational, such as setup, diagnostics, or release flow
- you already know the boundary and need proof, tests, or risk review instead

## Read Across The Package

- open [Architecture](../architecture/index.md) when you need the structure
  behind ingest preparation and workflow flow
- open [Interfaces](../interfaces/index.md) when you need the contracts that
  callers and downstream packages rely on
- open [Operations](../operations/index.md) when you need local workflow,
  validation, or release guidance
- open [Quality](../quality/index.md) when you need evidence that deterministic
  ingest behavior is actually protected

## Concrete Anchors

- `packages/bijux-canon-ingest` as the package root
- `packages/bijux-canon-ingest/src/bijux_canon_ingest` as the import boundary
- `packages/bijux-canon-ingest/tests` as the proof surface for owned behavior

## Reader Takeaway

Use `Foundation` to answer the ownership question with integrity: ingest exists
to make source material predictable enough for downstream retrieval work to
trust. If a proposal broadens ingest without making that preparation story
clearer, the design has probably crossed the boundary rather than improved it.

## Purpose

This page introduces the foundation handbook for `bijux-canon-ingest` and
routes readers to the specific boundary, language, and lifecycle pages that
explain why the package exists.
