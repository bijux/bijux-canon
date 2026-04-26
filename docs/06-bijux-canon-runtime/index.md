---
title: Runtime Handbook
audience: mixed
type: index
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Runtime Handbook

`bijux-canon-runtime` is the execution authority layer in `bijux-canon`. Start
here when the question is about run acceptance, replay policy, persistence, or
runtime-facing boundaries that sit above the rest of the package family.

This package is the place where the package family becomes governable as a run
system. It owns acceptance policy, replay authority, persistence boundaries,
and runtime-facing coordination that should remain explicit rather than hiding
in whichever lower package happened to execute last.

```mermaid
flowchart LR
    ingest["ingest"]
    index["index"]
    reason["reason"]
    agent["agent"]
    runtime["bijux-canon-runtime<br/>accept, persist, replay, govern"]
    reader["reader question<br/>what makes a run acceptable and durable?"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    class ingest,page runtime;
    class index,reason,agent,reader positive;
    ingest --> index --> reason --> agent --> runtime --> reader
```

## Read This Section When

- you need the package-level entrypoint for runtime docs
- you are checking execution, replay, or persistence behavior
- you want the shortest route into the owned runtime documentation
- you need to separate runtime authority from lower-package execution behavior

## What This Package Owns

- run acceptance and replay policy above the lower package family
- runtime persistence boundaries and durable runtime-facing artifacts
- the execution authority surface that sits above agent coordination

## What This Package Does Not Own

- ingest, index, reasoning, or agent-specific semantics inside their own
  package boundaries
- repository-wide maintainer automation that belongs in the maintenance
  handbook

## Choose The Next Section By Question

- open [Foundation](foundation/index.md) when the question is about package
  purpose, ownership, or vocabulary
- open [Architecture](architecture/index.md) when you need the module map,
  execution shape, or persistence structure
- open [Interfaces](interfaces/index.md) when the question is about commands,
  schemas, artifacts, or import surfaces
- open [Operations](operations/index.md) when you need setup, diagnostics,
  workflow, or release guidance
- open [Quality](quality/index.md) when the question is about trust, risk,
  invariants, or review standards

## Main Paths

- [Foundation](foundation/index.md)
- [Architecture](architecture/index.md)
- [Interfaces](interfaces/index.md)
- [Operations](operations/index.md)
- [Quality](quality/index.md)

## Reader Takeaway

Use this handbook when the real issue is whether a run is governed,
replay-aware, and durable enough to count as canonical runtime behavior rather
than merely as lower-package execution.
