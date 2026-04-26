---
title: Reasoning Handbook
audience: mixed
type: index
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Reasoning Handbook

`bijux-canon-reason` owns inspectable reasoning, verification, provenance, and
reasoning-side run artifacts. Use this handbook when you need to understand
how evidence becomes claims, checks, and durable reasoning output.

This package is where retrieval output becomes something a reviewer can inspect
as reasoning rather than as raw search results. It owns the conversion from
evidence into claims, verification steps, provenance-aware reasoning records,
and reasoning-side artifacts that should survive review.

```mermaid
flowchart LR
    retrieval["retrieval evidence and replayable results"]
    reason["bijux-canon-reason<br/>claims, checks, provenance"]
    agent["bijux-canon-agent<br/>workflow coordination"]
    runtime["bijux-canon-runtime<br/>run acceptance and persistence"]
    reader["reader question<br/>what can this reasoning output actually justify?"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    class retrieval,page reason;
    class agent,runtime,reader positive;
    retrieval --> reason --> agent --> runtime
    reason --> reader
```

## Use This Handbook When

- you need the package-level entrypoint for reasoning docs
- you are checking reasoning behavior, verification, or provenance
- you want the shortest route into the owned reasoning documentation
- you need to separate reasoning semantics from retrieval mechanics or runtime
  governance

## What This Package Owns

- claim formation and reasoning-side verification behavior
- provenance-aware reasoning artifacts and durable reasoning records
- the reasoning contracts that agent and runtime layers depend on

## What This Package Does Not Own

- ingest preparation or index execution behavior below the reasoning boundary
- agent orchestration policy above one reasoning step
- runtime acceptance, persistence, or run-governance behavior

## Choose A Section

- use [Foundation](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/) when the question is about package
  purpose, language, or ownership
- use [Architecture](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/) when you need the module map,
  execution flow, or dependency structure
- use [Interfaces](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/) when the question is about commands,
  schemas, artifacts, or import surfaces
- use [Operations](https://bijux.io/bijux-canon/04-bijux-canon-reason/operations/) when you need setup, diagnostics,
  local workflow, or release guidance
- use [Quality](https://bijux.io/bijux-canon/04-bijux-canon-reason/quality/) when the question is about trust, evidence,
  limitations, or review standards

## Pages In This Handbook

- [Foundation](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/)
- [Architecture](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/)
- [Interfaces](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/)
- [Operations](https://bijux.io/bijux-canon/04-bijux-canon-reason/operations/)
- [Quality](https://bijux.io/bijux-canon/04-bijux-canon-reason/quality/)

## Why Start Here

Use this handbook when the real issue is whether reasoning output is explicit,
verifiable, and provenance-aware enough to support later orchestration and
runtime decisions.
