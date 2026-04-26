---
title: Quality
audience: mixed
type: index
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Quality

Open this section when the question is how `bijux-canon-agent` earns trust:
which tests matter, which architectural invariants must survive, what trace and
artifact expectations are defended, and what still needs explicit skepticism
after a change.

This package does not prove itself only by “running once.” It has to show that
role behavior, pipeline control, trace integrity, schema contracts, and result
assembly still line up under unit, invariant, API, end-to-end, and sometimes
live-provider pressure.

## Start Here

- open [Test Strategy](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/test-strategy/) for the proof layers that matter most
  in this package
- open [Change Validation](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/change-validation/) when you need the validation
  bar for a real orchestration change
- open [Known Limitations](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/known-limitations/) and [Risk Register](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/risk-register/)
  before assuming agent output proves more than it actually does

## Pages In This Section

- [Test Strategy](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/test-strategy/)
- [Invariants](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/invariants/)
- [Review Checklist](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/review-checklist/)
- [Documentation Standards](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/documentation-standards/)
- [Definition of Done](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/definition-of-done/)
- [Dependency Governance](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/dependency-governance/)
- [Change Validation](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/change-validation/)
- [Known Limitations](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/known-limitations/)
- [Risk Register](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/risk-register/)

## Open Quality When

- you need to know what evidence should defend an orchestration change
- a review is really about trace trust, layering discipline, or result quality
- you need to decide whether a run is merely complete or actually believable

## Open Another Section When

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

- open [Foundation](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/) for package purpose and trust
  boundaries
- open [Architecture](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/) when a proof gap points to
  structural drift
- open [Interfaces](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/) when the evidence needs to defend a
  contract
- open [Operations](https://bijux.io/bijux-canon/05-bijux-canon-agent/operations/) when the validation bar depends on
  a repeatable workflow

## Bottom Line

Open `Quality` to ask whether the agent layer earned trust, not whether it
merely produced a run. The real bar is layering discipline, trace integrity,
schema and API stability, and clear limits that remain visible after the
change.

## What You Get

Open this page when you need the tests, invariants, review, validation, and
risk route through `bijux-canon-agent` before you inspect a specific trust
surface.
