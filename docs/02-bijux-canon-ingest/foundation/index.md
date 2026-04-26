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
retrieval-ready output. Open this section when the important question is not
which command to run, but why ingest owns this work at all and where that
ownership stops.

These pages help you distinguish source preparation from the downstream jobs
that index, reason over, or orchestrate the prepared output. Open them when
you need a clear explanation of why ingest exists without relying on tribal
memory.

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

- open [Package Overview](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/package-overview/) for the shortest explanation of
  what ingest is for
- open [Ownership Boundary](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/ownership-boundary/) when the issue might belong
  in index, reason, agent, or runtime instead
- open [Lifecycle Overview](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/lifecycle-overview/) when the real question is
  how source material moves through ingest before downstream packages pick it up

## Pages In This Section

- [Package Overview](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/package-overview/)
- [Scope and Non-Goals](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/scope-and-non-goals/)
- [Ownership Boundary](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/ownership-boundary/)
- [Repository Fit](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/repository-fit/)
- [Capability Map](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/capability-map/)
- [Domain Language](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/domain-language/)
- [Lifecycle Overview](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/lifecycle-overview/)
- [Dependencies and Adjacencies](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/dependencies-and-adjacencies/)
- [Change Principles](https://bijux.io/bijux-canon/02-bijux-canon-ingest/foundation/change-principles/)

## Open Foundation When

- you need the durable ownership story before reading code or command docs
- you are deciding whether deterministic preparation belongs in ingest or
  downstream retrieval behavior belongs elsewhere
- you need shared package language for chunking, source shaping, and handoff

## Open Another Section When

- the question is already about public commands, schemas, or artifact contracts
- the real problem is operational, such as setup, diagnostics, or release flow
- you already know the boundary and need proof, tests, or risk review instead

## Read Across The Package

- open [Architecture](https://bijux.io/bijux-canon/02-bijux-canon-ingest/architecture/) when you need the structure
  behind ingest preparation and workflow flow
- open [Interfaces](https://bijux.io/bijux-canon/02-bijux-canon-ingest/interfaces/) when you need the contracts that
  callers and downstream packages rely on
- open [Operations](https://bijux.io/bijux-canon/02-bijux-canon-ingest/operations/) when you need local workflow,
  validation, or release guidance
- open [Quality](https://bijux.io/bijux-canon/02-bijux-canon-ingest/quality/) when you need evidence that deterministic
  ingest behavior is actually protected

## Concrete Anchors

- `packages/bijux-canon-ingest` as the package root
- `packages/bijux-canon-ingest/src/bijux_canon_ingest` as the import boundary
- `packages/bijux-canon-ingest/tests` as the proof surface for owned behavior

## Bottom Line

Open `Foundation` to answer the ownership question with integrity: ingest exists
to make source material predictable enough for downstream retrieval work to
trust. If a proposal broadens ingest without making that preparation story
clearer, the design has probably crossed the boundary rather than improved it.

## What You Get

Open this page when you need the boundary, language, and lifecycle route into
`bijux-canon-ingest` before you move on to commands, structure, or proof.
