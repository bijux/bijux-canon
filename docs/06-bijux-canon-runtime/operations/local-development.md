---
title: Local Development
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-04
---

# Local Development

Local development should happen inside `packages/bijux-canon-runtime` with tests and docs updated
in the same change series as the code.

The point is not to prescribe one favorite workflow. It is to keep local work
close enough to the owning package that changes remain easy to explain and easy
to validate before they spread outward.

Treat the operations pages for `bijux-canon-runtime` as the package's explicit operating memory. They make common tasks repeatable without relearning the workflow from logs or oral history.

## Visual Summary

```mermaid
flowchart LR
    root["Work in package root<br/>packages/bijux-canon-runtime"]
    change["Change code and docs together"]
    tests["Run local proof<br/>tests/unit for api, contracts, core"]
    commit["Commit when one intent is coherent"]
    root --> change --> tests --> commit
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class root anchor;
    class change page;
    class tests positive;
    class commit action;
```

## Development Anchors

- tests/unit for api, contracts, core, interfaces, model, and runtime
- tests/e2e for governed flow behavior
- tests/regression and tests/smoke for replay and storage protection
- tests/golden for durable example fixtures

## Concrete Anchors

- `packages/bijux-canon-runtime/pyproject.toml` for package metadata
- `packages/bijux-canon-runtime/README.md` for local package framing
- `packages/bijux-canon-runtime/tests` for executable operational backstops

## Open This Page When

- you are installing, running, diagnosing, or releasing the package
- you need repeatable operational anchors rather than architectural framing
- you are responding to package behavior in local work, CI, or incident pressure

## Decision Rule

Use `Local Development` to decide whether a maintainer can repeat the package workflow from checked-in assets instead of memory. If a step works only because someone already knows the trick, the workflow is not documented clearly enough yet.

## What This Page Answers

- how `bijux-canon-runtime` is installed, run, diagnosed, and released in practice
- which checked-in files and tests anchor the operational story
- where a maintainer should look first when the package behaves differently

## Reviewer Lens

- verify that setup, workflow, and release statements still match package metadata and current commands
- check that operational guidance still points at real diagnostics and validation paths
- confirm that maintainer advice still works under current local and CI expectations

## Honesty Boundary

This page shows how `bijux-canon-runtime` is operated, but it does not replace
package metadata, actual runtime behavior, or validation in a real
environment. A workflow is only trustworthy if a maintainer can still repeat
it from the checked-in assets named here.

## Next Checks

- open interfaces when the operational path depends on a specific surface contract
- open quality when the question becomes whether the workflow is sufficiently proven
- move back to architecture when operational complexity suggests a structural problem

