---
title: Agent Handbook
audience: mixed
type: index
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Agent Handbook

`bijux-canon-agent` owns deterministic agent orchestration, workflow coordination, and trace-producing execution surfaces. It turns reasoning-capable steps into inspectable multi-step behavior without pretending that orchestration itself is runtime authority.

The main failure this handbook prevents is letting orchestration blur into either reasoning semantics below or runtime governance above. When those lines drift, readers can no longer tell whether a surprising behavior came from a decision, a workflow, or a run policy.

## What The Reader Should See First

Agent is the workflow coordination layer. It decides how role-specific steps
are ordered, how intermediate outputs are checked, and which trace proves what
happened. It should make multi-step behavior visible without becoming the owner
of retrieval truth, reasoning meaning, or final runtime acceptance.

```mermaid
flowchart LR
    inputs["reasoning artifacts<br/>claims, checks, context"]
    plan["execution plan<br/>roles, stages, stop rules"]
    roles["agent roles<br/>planner, verifier, critique, summarizer"]
    kernel["execution kernel<br/>ordered calls and lifecycle"]
    trace["workflow trace<br/>events, hashes, replay fields"]
    runtime["runtime package<br/>acceptance and replay authority"]

    inputs --> plan --> roles --> kernel --> trace --> runtime
    roles -. validated by .-> validation["trace validation"]
    kernel -. emits .-> telemetry["telemetry and result artifacts"]

    classDef page fill:#eef6ff,stroke:#2563eb,color:#153145,stroke-width:2px;
    classDef positive fill:#eefbf3,stroke:#16a34a,color:#173622;
    classDef anchor fill:#f4f0ff,stroke:#7c3aed,color:#47207f;
    classDef action fill:#fff4da,stroke:#d97706,color:#6b3410;
    class inputs page;
    class plan,roles,kernel positive;
    class trace,validation,telemetry anchor;
    class runtime action;
```

## What This Package Owns

- coordination of agent roles, steps, and deterministic workflow progression
- trace-producing orchestration surfaces that explain what the agent did and in what order
- agent-facing contracts that sit above reasoning and below runtime governance

## What This Package Does Not Own

- retrieval and reasoning semantics in the lower package family
- acceptance, persistence, and replay authority for governed runs
- repository-wide maintainer automation and release governance

## Boundary Test

If the change decides how roles coordinate, which step runs next, or what trace a workflow must emit, it belongs here. If the change decides what a claim means or whether a whole run counts, it belongs elsewhere.

## First Proof Check

- `packages/bijux-canon-agent/src/bijux_canon_agent` for the orchestration implementation boundary
- `packages/bijux-canon-agent/src/bijux_canon_agent/pipeline` for workflow planning, execution, convergence, and finalization
- `packages/bijux-canon-agent/src/bijux_canon_agent/traces` for trace serialization and replayability
- `packages/bijux-canon-agent/tests` for proof that coordination remains deterministic and inspectable
- `apis/bijux-canon-agent/v1/schema.yaml` for the tracked caller-facing schema

## Start Here

- open [Foundation](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/) when the question is why this package exists or where its ownership stops
- open [Architecture](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/) when you need module boundaries, dependency flow, or execution shape
- open [Interfaces](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/) when the question is about commands, APIs, schemas, imports, or artifacts that callers may treat as stable
- open [Operations](https://bijux.io/bijux-canon/05-bijux-canon-agent/operations/) when you need local workflow, diagnostics, release, or recovery guidance
- open [Quality](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/) when the question is whether the package has proved its promises strongly enough

## Pages In This Package

- [Foundation](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/)
- [Architecture](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/)
- [Interfaces](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/)
- [Operations](https://bijux.io/bijux-canon/05-bijux-canon-agent/operations/)
- [Quality](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/)

## Bottom Line

If a proposed change makes `bijux-canon-agent` broader without making its owned role easier to defend, the change is probably crossing a package boundary rather than improving the design.
