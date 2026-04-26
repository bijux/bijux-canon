---
title: Architecture
audience: mixed
type: index
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Architecture

Open this section when the question is structural: where claims and checks are formed, how reasoning steps flow through the package, and how the code keeps meaning visible instead of scattering it.

## Structural Shape

Reason architecture centers on explicit reasoning artifacts. Core models define
claims, plans, traces, and verification results; execution modules run steps
and tools; verification modules check structure and provenance; trace modules
make the result replayable rather than just plausible.

```mermaid
flowchart LR
    evidence["evidence input<br/>retrieved chunks and context"]
    core["core models<br/>claims, plans, verification, traces"]
    execution["execution<br/>runtime, tools, step executor"]
    reasoning["reasoning<br/>extractive and backend logic"]
    verification["verification<br/>structural and provenance checks"]
    traces["traces<br/>checksum, replay, diff"]
    output["reasoning artifact<br/>claims, checks, metadata"]

    evidence --> core --> execution --> reasoning --> verification --> output
    execution --> traces --> output
    core -. schemas meaning .-> output

    classDef page fill:#eef6ff,stroke:#2563eb,color:#153145,stroke-width:2px;
    classDef positive fill:#eefbf3,stroke:#16a34a,color:#173622;
    classDef anchor fill:#f4f0ff,stroke:#7c3aed,color:#47207f;
    classDef action fill:#fff4da,stroke:#d97706,color:#6b3410;
    class evidence page;
    class core,execution,reasoning,verification positive;
    class traces anchor;
    class output action;
```

## Read These First

- open [Module Map](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/module-map/) first when you need the owning code area for a reasoning concern
- open [Execution Model](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/execution-model/) when you need the path from evidence input to reasoning output
- open [Integration Seams](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/integration-seams/) when a change could blur retrieval, orchestration, or runtime boundaries

## Structural Risk

The main architectural risk here is hiding reasoning policy in the wrong layer until no one can point to the module that actually decided what a claim means.

## First Proof Check

- `packages/bijux-canon-reason/src/bijux_canon_reason/core/models` for claims, planning, trace, and verification models
- `packages/bijux-canon-reason/src/bijux_canon_reason/execution` for runtime and tool execution boundaries
- `packages/bijux-canon-reason/src/bijux_canon_reason/verification` for checks that keep claims reviewable
- `packages/bijux-canon-reason/tests` for proof that claims, checks, and provenance stay aligned


## Pages In This Section

- [Module Map](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/module-map/)
- [Dependency Direction](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/dependency-direction/)
- [Execution Model](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/execution-model/)
- [State and Persistence](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/state-and-persistence/)
- [Integration Seams](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/integration-seams/)
- [Error Model](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/error-model/)
- [Extensibility Model](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/extensibility-model/)
- [Code Navigation](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/code-navigation/)
- [Architecture Risks](https://bijux.io/bijux-canon/04-bijux-canon-reason/architecture/architecture-risks/)

## Leave This Section When

- leave for [Interfaces](https://bijux.io/bijux-canon/04-bijux-canon-reason/interfaces/) when the structural question is already a public contract question
- leave for [Operations](https://bijux.io/bijux-canon/04-bijux-canon-reason/operations/) when the issue is running, diagnosing, or releasing the package rather than explaining its shape
- leave for [Quality](https://bijux.io/bijux-canon/04-bijux-canon-reason/quality/) when the structure is clear and the real question is whether the package has proved it strongly enough

## Bottom Line

A structure that cannot be explained in one pass is already carrying too much hidden policy.
