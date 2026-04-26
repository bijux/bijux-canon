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

These pages explain the proof story for `bijux-canon-runtime`. They make
trust, skepticism, and review pressure visible enough that passing checks do
not get mistaken for sufficient evidence.

Runtime quality is not only about unit correctness. It is also about whether
execution traces, replay behavior, verification arbitration, and persistence
rules still justify trusting a governed run.

## Start Here

- open [Test Strategy](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/test-strategy/) for the shortest explanation of the
  runtime proof stack
- open [Invariants](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/invariants/) when a change could disturb replay,
  persistence, or determinism claims
- open [Change Validation](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/change-validation/) when the question is what to
  run for one concrete runtime change
- open [Known Limitations](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/known-limitations/) and [Risk Register](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/risk-register/)
  before claiming the package proves more than it currently does

## Pages In This Section

- [Test Strategy](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/test-strategy/)
- [Invariants](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/invariants/)
- [Review Checklist](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/review-checklist/)
- [Documentation Standards](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/documentation-standards/)
- [Definition of Done](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/definition-of-done/)
- [Dependency Governance](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/dependency-governance/)
- [Change Validation](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/change-validation/)
- [Known Limitations](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/known-limitations/)
- [Risk Register](https://bijux.io/bijux-canon/06-bijux-canon-runtime/quality/risk-register/)

## Open This Section When

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

## Across This Package

- open [Interfaces](https://bijux.io/bijux-canon/06-bijux-canon-runtime/interfaces/) when the proof question becomes
  about a named CLI, API, schema, or artifact contract
- open [Operations](https://bijux.io/bijux-canon/06-bijux-canon-runtime/operations/) when the needed evidence depends on
  a repeatable runtime workflow
- open [Architecture](https://bijux.io/bijux-canon/06-bijux-canon-runtime/architecture/) when the proof gap points to
  structural drift rather than missing checks

## Bottom Line

Open this section to decide whether runtime has actually earned trust after a
change. If one narrow green check hides a wider replay, persistence, contract,
or validation gap, the work is not done yet.

