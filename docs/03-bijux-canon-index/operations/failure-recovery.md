---
title: Failure Recovery
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Failure Recovery

Failure recovery starts with knowing which artifacts, interfaces, and tests expose the problem.

This page helps a maintainer stabilize the situation before trying to improve
it. The first question is not always how to fix the bug; it is how to locate
the right evidence quickly.

Treat the operations pages for `bijux-canon-index` as the package's explicit operating memory. They should make common tasks repeatable without relearning the workflow from logs or oral history.

## Visual Summary

```mermaid
flowchart LR
    incident["Failure or incident"]
    entry["Check entry surface<br/>CLI modules under src/bijux_canon_index/interfaces/cli"]
    evidence["Inspect evidence<br/>vector execution result collections"]
    rerun["Reproduce with proof<br/>tests/e2e for CLI workflows, API"]
    incident --> entry --> evidence --> rerun
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class incident page;
    class entry anchor;
    class evidence action;
    class rerun positive;
```

## Recovery Anchors

- interface surfaces: CLI modules under src/bijux_canon_index/interfaces/cli, HTTP app under src/bijux_canon_index/api, OpenAPI schema files under apis/bijux-canon-index/v1
- artifacts to inspect: vector execution result collections, provenance and replay comparison reports, backend-specific metadata and audit output
- tests to run: tests/unit for API, application, contracts, domain, infra, and tooling, tests/e2e for CLI workflows, API smoke, determinism gates, and provenance gates

## Concrete Anchors

- `packages/bijux-canon-index/pyproject.toml` for package metadata
- `packages/bijux-canon-index/README.md` for local package framing
- `packages/bijux-canon-index/tests` for executable operational backstops

## Open This Page When

- you are installing, running, diagnosing, or releasing the package
- you need repeatable operational anchors rather than architectural framing
- you are responding to package behavior in local work, CI, or incident pressure

## Decision Rule

Use `Failure Recovery` to decide whether a maintainer can repeat the package workflow from checked-in assets instead of memory. If a step works only because someone already knows the trick, the workflow is not documented clearly enough yet.

## What This Page Answers

- how `bijux-canon-index` is installed, run, diagnosed, and released in practice
- which checked-in files and tests anchor the operational story
- where a maintainer should look first when the package behaves differently

## Reviewer Lens

- verify that setup, workflow, and release statements still match package metadata and current commands
- check that operational guidance still points at real diagnostics and validation paths
- confirm that maintainer advice still works under current local and CI expectations

## Honesty Boundary

This page shows how `bijux-canon-index` is operated, but it does not replace
package metadata, actual runtime behavior, or validation in a real
environment. A workflow is only trustworthy if a maintainer can still repeat
it from the checked-in assets named here.

## Next Checks

- open interfaces when the operational path depends on a specific surface contract
- open quality when the question becomes whether the workflow is sufficiently proven
- move back to architecture when operational complexity suggests a structural problem

## Purpose

This page shows the durable frame readers can use to triage package failures.

## Stability

Keep it aligned with the package entrypoints and diagnostic outputs.
