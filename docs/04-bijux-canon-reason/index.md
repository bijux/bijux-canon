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
reasoning-side run artifacts. Start here when the question is about how
evidence becomes claims, checks, and durable reasoning output.

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

## Read This Section When

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

## Choose The Next Section By Question

- open [Foundation](foundation/index.md) when the question is about package
  purpose, language, or ownership
- open [Architecture](architecture/index.md) when you need the module map,
  execution flow, or dependency structure
- open [Interfaces](interfaces/index.md) when the question is about commands,
  schemas, artifacts, or import surfaces
- open [Operations](operations/index.md) when you need setup, diagnostics,
  local workflow, or release guidance
- open [Quality](quality/index.md) when the question is about trust, evidence,
  limitations, or review standards

## Main Paths

- [Foundation](foundation/index.md)
- [Architecture](architecture/index.md)
- [Interfaces](interfaces/index.md)
- [Operations](operations/index.md)
- [Quality](quality/index.md)

## Reader Takeaway

Use this handbook when the real issue is whether reasoning output is explicit,
verifiable, and provenance-aware enough to support later orchestration and
runtime decisions.
