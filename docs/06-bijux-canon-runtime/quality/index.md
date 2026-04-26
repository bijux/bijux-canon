---
title: Quality
audience: mixed
type: index
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-26
---

# Quality

Open this section to understand how `bijux-canon-runtime` earns trust: which
proof surfaces matter, which risks stay visible, and what done should mean
after a real change.

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

- open [Test Strategy](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/test-strategy/) for the shortest explanation of the
  runtime proof stack
- open [Invariants](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/invariants/) when a change could disturb replay,
  persistence, or determinism claims
- open [Change Validation](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/change-validation/) when the question is what to
  run for one concrete runtime change
- open [Known Limitations](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/known-limitations/) and [Risk Register](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/risk-register/)
  before claiming the package proves more than it currently does

## Pages In Quality

- [Test Strategy](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/test-strategy/)
- [Invariants](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/invariants/)
- [Review Checklist](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/review-checklist/)
- [Documentation Standards](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/documentation-standards/)
- [Definition of Done](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/definition-of-done/)
- [Dependency Governance](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/dependency-governance/)
- [Change Validation](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/change-validation/)
- [Known Limitations](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/known-limitations/)
- [Risk Register](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/risk-register/)

## Open Quality When

- you are reviewing tests, invariants, limitations, or ongoing risks
- you need evidence that the documented contract is actually defended
- you are deciding whether a change is truly done rather than merely implemented

## Open Another Section When

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

- open [Interfaces](https://bijux.io/bijux-canon/06-bijux-canon-runtime/interfaces/) when the proof question becomes
  about a named CLI, API, schema, or artifact contract
- open [Operations](https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/) when the needed evidence depends on
  a repeatable runtime workflow
- open [Architecture](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/) when the proof gap points to
  structural drift rather than missing checks

## Why Use Quality

Open `Quality` to decide whether runtime has actually earned trust after a
change. If one narrow green check hides a wider replay, persistence, contract,
or validation gap, the work is not done yet.

## What You Get

Open this page when you need the tests, invariants, review, validation, and
risk route through `bijux-canon-runtime` before you inspect a specific trust
surface.
