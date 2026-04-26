---
title: Architecture
audience: mixed
type: index
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Architecture

Open this section when the question is structural: which modules own planning,
retrieval, reasoning, verification, interfaces, and traces, and how a run
flows through those pieces without smearing responsibilities together.

`bijux-canon-reason` is easiest to read when you treat it as a pipeline of
responsibility rather than as a flat package tree. Planning shapes intent,
retrieval assembles evidence views, execution and reasoning apply tools and
claim semantics, verification challenges the result, and traces preserve what
happened for replay or review.

## Visual Summary

```mermaid
flowchart TB
    intent["planning and IR"]
    corpus["retrieval and corpus shaping"]
    execs["execution runtime and tool dispatch"]
    semantics["reasoning semantics and claim logic"]
    checks["verification checks and contexts"]
    traces["trace, replay, and artifact surfaces"]
    reader["reader question<br/>where does this reasoning behavior actually live?"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    class intent,page reader;
    class corpus,execs,semantics positive;
    class checks,traces anchor;
    intent --> corpus --> execs --> semantics --> checks --> traces
    corpus --> reader
    execs --> reader
    semantics --> reader
    checks --> reader
```

## Start Here

- open [Module Map](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/module-map/) for the shortest route from directory names
  to owned behavior
- open [Execution Model](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/execution-model/) when you need the reasoning
  lifecycle from plan to verified output
- open [State and Persistence](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/state-and-persistence/) when the question is
  which records become replayable or durable

## Pages In Architecture

- [Module Map](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/module-map/)
- [Dependency Direction](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/dependency-direction/)
- [Execution Model](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/execution-model/)
- [State and Persistence](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/state-and-persistence/)
- [Integration Seams](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/integration-seams/)
- [Error Model](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/error-model/)
- [Extensibility Model](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/extensibility-model/)
- [Code Navigation](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/code-navigation/)
- [Architecture Risks](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/architecture-risks/)

## Use Architecture When

- you need to know which module family owns a behavior before editing it
- a review comment names structure, layering, or execution drift rather than a
  single bug
- you need to explain how planning, retrieval, reasoning, verification, and
  trace code relate

## Open Another Section When

- the main question is why the package owns the behavior at all
- you are deciding whether a CLI, API, or trace file is a supported contract
- the real concern is how to run, validate, or release the package

## Read Across The Package

- open [Foundation](https://bijux.io/bijux-canon/04-bijux-canon-reason/foundation/) for package purpose and ownership
  boundaries
- open [Interfaces](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/) for CLI, API, schema, and artifact
  contracts
- open [Operations](https://bijux.io/bijux-canon/04-bijux-canon-reason/operations/) for install, replay, diagnostics,
  and release procedures
- open [Quality](https://bijux.io/bijux-canon/04-bijux-canon-reason/quality/) for invariants, tests, and structural
  risk pressure

## Concrete Anchors

- `src/bijux_canon_reason/planning` for plan construction and intermediate
  representation
- `src/bijux_canon_reason/retrieval` for corpus, chunking, and BM25-backed
  evidence shaping
- `src/bijux_canon_reason/execution` for step execution, runtime, and tool
  dispatch
- `src/bijux_canon_reason/reasoning`, `verification`, and `traces` for claim
  semantics, checks, and replayable records

## Why Use Architecture

Open `Architecture` when you need the package to read as a sequence of named
responsibilities, not a tangle of utilities. If a change blurs planning,
evidence shaping, claim logic, verification, and traces into one layer, the
design is getting weaker even if tests still pass.

## What You Get

Open this page when you need the module, dependency, execution, and
durable-state route through `bijux-canon-reason` before you inspect a specific
structural topic.
