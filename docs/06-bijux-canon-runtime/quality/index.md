---
title: Quality
audience: mixed
type: index
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Quality

This section explains how `bijux-canon-runtime` earns trust: which proof surfaces matter, which risks stay visible, and what done should mean after a real change.

These pages explain the proof story for `bijux-canon-runtime`. They should make
trust, skepticism, and review pressure visible enough that passing checks do
not get mistaken for sufficient evidence.

Runtime quality is not only about unit correctness. It is also about whether
execution traces, replay behavior, verification arbitration, and persistence
rules still justify trusting a governed run.

## Visual Summary

```mermaid
flowchart LR
    reader["reader question<br/>what evidence makes a runtime change believable?"]
    strategy["proof layers<br/>unit, contracts, api, e2e, regression"]
    invariants["what must not drift<br/>replay, determinism, persistence"]
    review["review bars<br/>verification and acceptability"]
    risks["limits and remaining uncertainty"]
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    class reader page;
    class strategy,invariants,review positive;
    class risks caution;
    reader --> strategy
    reader --> invariants
    reader --> review
    reader --> risks
```

## Start Here

- open [Test Strategy](test-strategy.md) for the shortest explanation of the
  runtime proof stack
- open [Invariants](invariants.md) when a change could disturb replay,
  persistence, or determinism claims
- open [Change Validation](change-validation.md) when the question is what to
  run for one concrete runtime change
- open [Known Limitations](known-limitations.md) and [Risk Register](risk-register.md)
  before claiming the package proves more than it currently does

## Pages in This Section

- [Test Strategy](test-strategy.md)
- [Invariants](invariants.md)
- [Review Checklist](review-checklist.md)
- [Documentation Standards](documentation-standards.md)
- [Definition of Done](definition-of-done.md)
- [Dependency Governance](dependency-governance.md)
- [Change Validation](change-validation.md)
- [Known Limitations](known-limitations.md)
- [Risk Register](risk-register.md)

## Use This Page When

- you are reviewing tests, invariants, limitations, or ongoing risks
- you need evidence that the documented contract is actually defended
- you are deciding whether a change is truly done rather than merely implemented

## Do Not Use This Section When

- the real question is still why runtime owns a behavior at all
- you need module layout or procedure before you can evaluate the proof
- you are still deciding what the public contract is rather than whether it is
  defended

## Concrete Anchors

- `tests/unit/runtime/`, `tests/unit/contracts/`, and `tests/unit/api/` for
  the narrow contract and model proof layers
- `tests/e2e/` for governed execution behavior
- `tests/regression/` for replay, persistence, determinism, and compatibility
  drift protection
- `apis/bijux-canon-runtime/v1/schema.yaml` and
  `src/bijux_canon_runtime/observability/schema.sql` for two of the highest
  value frozen surfaces quality must defend

## Read Across The Package

- open [Interfaces](../interfaces/index.md) when the proof question becomes
  about a named CLI, API, schema, or artifact contract
- open [Operations](../operations/index.md) when the needed evidence depends on
  a repeatable runtime workflow
- open [Architecture](../architecture/index.md) when the proof gap points to
  structural drift rather than missing checks

## Reader Takeaway

Use `Quality` to decide whether runtime has actually earned trust after a
change. If one narrow green check hides a wider replay, persistence, contract,
or validation gap, the work is not done yet.

## Purpose

This page explains how to use the quality section for `bijux-canon-runtime`
without repeating the detail that belongs on the topic pages beneath it.
