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

For many readers this is the page that explains whether a run counts at all.
It should make the package role obvious quickly: lower packages can execute
work, but runtime decides whether that work is acceptable, replayable, durable,
and fit to keep.

```mermaid
flowchart LR
    reader["reader question<br/>what makes a run acceptable and durable?"]
    ingest["ingest"]
    index["index"]
    reason["reason"]
    agent["agent"]
    runtime["bijux-canon-runtime<br/>accept, persist, replay, govern"]
    artifacts["execution traces, envelopes, and durable state"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    class reader page;
    class ingest,index,reason,agent positive;
    class runtime anchor;
    class artifacts positive;
    ingest --> index --> reason --> agent --> runtime
    runtime --> artifacts
    artifacts --> reader
```

## Start Here

- open [Foundation](foundation/index.md) when the question is why runtime owns
  run authority instead of one lower package
- open [Architecture](architecture/index.md) when you need the execution and
  persistence structure
- open [Interfaces](interfaces/index.md) when the question is about CLI, API,
  schemas, or durable artifact contracts
- open [Quality](quality/index.md) when the issue is whether runtime has proven
  a run acceptable rather than merely executable

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

## Concrete Anchors

- `src/bijux_canon_runtime/application/execute_flow.py` for the main execution
  authority entrypoint
- `src/bijux_canon_runtime/runtime/execution/` for governed run lifecycle work
- `src/bijux_canon_runtime/observability/` for replay, trace, and durable
  runtime records
- `tests/e2e/` and `tests/regression/` for the highest-value proof that a run
  remains replayable and acceptable

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
than merely as lower-package execution. If the question stops at “did code run”
rather than “can this run be accepted and replayed,” you are probably still in
the wrong package.
