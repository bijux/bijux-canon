---
title: Quality
audience: mixed
type: index
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Quality

Use this section when the question is how `bijux-canon-agent` earns trust:
which tests matter, which architectural invariants must survive, what trace and
artifact expectations are defended, and what still needs explicit skepticism
after a change.

This package does not prove itself only by “running once.” It has to show that
role behavior, pipeline control, trace integrity, schema contracts, and result
assembly still line up under unit, invariant, API, end-to-end, and sometimes
live-provider pressure.

## Visual Summary

```mermaid
flowchart LR
    units["unit tests for agents, pipeline, traces, and results"]
    invariants["invariant tests for layering and package discipline"]
    api["API and schema contract tests"]
    e2e["end-to-end orchestration scenarios"]
    live["optional live-provider and integration pressure"]
    reader["reader question<br/>what evidence makes this orchestrated run trustworthy?"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    class units,page reader;
    class invariants,api,e2e positive;
    class live caution;
    units --> reader
    invariants --> reader
    api --> reader
    e2e --> reader
    live --> reader
```

## Start Here

- use [Test Strategy](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/test-strategy/) for the proof layers that matter most
  in this package
- use [Change Validation](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/change-validation/) when you need the validation
  bar for a real orchestration change
- use [Known Limitations](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/known-limitations/) and [Risk Register](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/risk-register/)
  before assuming agent output proves more than it actually does

## Pages In Quality

- [Test Strategy](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/test-strategy/)
- [Invariants](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/invariants/)
- [Review Checklist](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/review-checklist/)
- [Documentation Standards](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/documentation-standards/)
- [Definition of Done](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/definition-of-done/)
- [Dependency Governance](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/dependency-governance/)
- [Change Validation](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/change-validation/)
- [Known Limitations](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/known-limitations/)
- [Risk Register](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/risk-register/)

## Use Quality When

- you need to know what evidence should defend an orchestration change
- a review is really about trace trust, layering discipline, or result quality
- you need to decide whether a run is merely complete or actually believable

## Move On When

- the main problem is package ownership or boundary confusion
- you are still locating modules or public contracts
- the issue is primarily procedural rather than evidentiary

## Concrete Anchors

- `tests/unit` for local behavior across agents, pipeline, traces, results, and
  validators
- `tests/invariants` for layering, import, artifact, and package-discipline
  rules
- `tests/api`, `tests/e2e`, and `tests/integration/test_deepseek_live.py` for
  contract, scenario, and live-provider pressure

## Read Across The Package

- use [Foundation](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/) for package purpose and trust
  boundaries
- use [Architecture](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/) when a proof gap points to
  structural drift
- use [Interfaces](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/) when the evidence needs to defend a
  contract
- use [Operations](https://bijux.io/bijux-canon/05-bijux-canon-agent/operations/) when the validation bar depends on
  a repeatable workflow

## Why Use Quality

Use `Quality` to ask whether the agent layer earned trust, not whether it
merely produced a run. The real bar is layering discipline, trace integrity,
schema and API stability, and clear limits that remain visible after the
change.

## What You Get

This page gives you the tests, invariants, review, validation, and risk route
through `bijux-canon-agent` before you inspect a specific trust surface.
