---
title: Architecture
audience: mixed
type: index
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Architecture

Use this section when the question is structural: which modules own planning,
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

- open [Module Map](module-map.md) for the shortest route from directory names
  to owned behavior
- open [Execution Model](execution-model.md) when you need the reasoning
  lifecycle from plan to verified output
- open [State and Persistence](state-and-persistence.md) when the question is
  which records become replayable or durable

## Pages In This Section

- [Module Map](module-map.md)
- [Dependency Direction](dependency-direction.md)
- [Execution Model](execution-model.md)
- [State and Persistence](state-and-persistence.md)
- [Integration Seams](integration-seams.md)
- [Error Model](error-model.md)
- [Extensibility Model](extensibility-model.md)
- [Code Navigation](code-navigation.md)
- [Architecture Risks](architecture-risks.md)

## Use This Section When

- you need to know which module family owns a behavior before editing it
- a review comment names structure, layering, or execution drift rather than a
  single bug
- you need to explain how planning, retrieval, reasoning, verification, and
  trace code relate

## Do Not Use This Section When

- the main question is why the package owns the behavior at all
- you are deciding whether a CLI, API, or trace file is a supported contract
- the real concern is how to run, validate, or release the package

## Read Across The Package

- open [Foundation](../foundation/index.md) for package purpose and ownership
  boundaries
- open [Interfaces](../interfaces/index.md) for CLI, API, schema, and artifact
  contracts
- open [Operations](../operations/index.md) for install, replay, diagnostics,
  and release procedures
- open [Quality](../quality/index.md) for invariants, tests, and structural
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

## Reader Takeaway

`Architecture` should make the package readable as a sequence of named
responsibilities, not a tangle of utilities. If a change blurs planning,
evidence shaping, claim logic, verification, and traces into one layer, the
design is getting weaker even if tests still pass.

## Purpose

This page introduces the reasoning architecture handbook and routes readers to
the pages that explain module groups, dependency direction, execution flow, and
durable state.
