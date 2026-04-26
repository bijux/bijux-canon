---
title: Agent Handbook
audience: mixed
type: index
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Agent Handbook

`bijux-canon-agent` owns deterministic agent orchestration, workflow
coordination, and trace-producing execution surfaces. Open this handbook when
you need to understand agent behavior rather than runtime governance around
it.

This package is where reasoning-capable steps become coordinated agent
workflows. It owns orchestration behavior that should stay deterministic,
trace-producing, and inspectable enough that readers can tell what an agent did
without confusing that orchestration layer with the deeper runtime authority.

```mermaid
flowchart LR
    reason["reasoning results and checks"]
    agent["bijux-canon-agent<br/>coordinate, trace, orchestrate"]
    runtime["bijux-canon-runtime<br/>accept, persist, govern runs"]
    reader["reader question<br/>what did the agent actually coordinate?"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    class reason,page agent;
    class runtime,reader positive;
    reason --> agent --> runtime
    agent --> reader
```

## Use This Handbook When

- you need the package-level entrypoint for agent docs
- you are checking orchestration, agent APIs, or trace-producing workflows
- you want the shortest route into the owned agent documentation
- you need to separate orchestration behavior from reasoning semantics or
  runtime acceptance policy

## What This Package Owns

- deterministic coordination of agent workflows and steps
- trace-producing orchestration surfaces that make execution inspectable
- agent-facing contracts that sit above reasoning and below runtime governance

## What This Package Does Not Own

- retrieval and reasoning semantics in the lower package family
- top-level runtime acceptance, persistence, or replay authority
- repository-wide maintainer governance above the package boundary

## Choose A Section

- use [Foundation](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/) when the question is about package
  purpose, language, or scope
- use [Architecture](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/) when you need module boundaries,
  dependency direction, or execution flow
- use [Interfaces](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/) when the question is about commands,
  schemas, artifacts, or import surfaces
- use [Operations](https://bijux.io/bijux-canon/05-bijux-canon-agent/operations/) when you need setup, diagnostics,
  workflow, or release guidance
- use [Quality](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/) when you need trust posture, proof
  expectations, or review standards

## Pages In This Handbook

- [Foundation](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/)
- [Architecture](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/)
- [Interfaces](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/)
- [Operations](https://bijux.io/bijux-canon/05-bijux-canon-agent/operations/)
- [Quality](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/)

## Why Start Here

Open this handbook when the meaningful question is how agent behavior is
coordinated and traced. If the question is really about whether a run should be
accepted, replayed, or persisted, move up to the runtime handbook instead.
