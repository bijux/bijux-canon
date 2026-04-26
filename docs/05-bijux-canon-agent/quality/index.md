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

- open [Test Strategy](test-strategy.md) for the proof layers that matter most
  in this package
- open [Change Validation](change-validation.md) when you need the validation
  bar for a real orchestration change
- open [Known Limitations](known-limitations.md) and [Risk Register](risk-register.md)
  before assuming agent output proves more than it actually does

## Pages In This Section

- [Test Strategy](test-strategy.md)
- [Invariants](invariants.md)
- [Review Checklist](review-checklist.md)
- [Documentation Standards](documentation-standards.md)
- [Definition of Done](definition-of-done.md)
- [Dependency Governance](dependency-governance.md)
- [Change Validation](change-validation.md)
- [Known Limitations](known-limitations.md)
- [Risk Register](risk-register.md)

## Use This Section When

- you need to know what evidence should defend an orchestration change
- a review is really about trace trust, layering discipline, or result quality
- you need to decide whether a run is merely complete or actually believable

## Do Not Use This Section When

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

- open [Foundation](../foundation/index.md) for package purpose and trust
  boundaries
- open [Architecture](../architecture/index.md) when a proof gap points to
  structural drift
- open [Interfaces](../interfaces/index.md) when the evidence needs to defend a
  contract
- open [Operations](../operations/index.md) when the validation bar depends on
  a repeatable workflow

## Reader Takeaway

Use `Quality` to ask whether the agent layer earned trust, not whether it
merely produced a run. The real bar is layering discipline, trace integrity,
schema and API stability, and clear limits that remain visible after the
change.

## Purpose

This page introduces the agent quality handbook and routes readers to the pages
that explain tests, invariants, review standards, validation, and known
limits.
