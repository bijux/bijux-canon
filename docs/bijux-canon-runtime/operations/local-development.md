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

Treat the operations pages for `bijux-canon-runtime` as the package's explicit operating memory. They should make common tasks repeatable without relearning the workflow from logs or oral history.

## Page Maps

```mermaid
flowchart LR
    context["bijux-canon-runtime / Operations"]
    page["Local Development"]
    follow["Follow the narrowest next route"]
    classDef context fill:#eef2ff,stroke:#4f46e5,color:#1e2852;
    classDef page fill:#e0e7ff,stroke:#3730a3,color:#1e2852,stroke-width:2px;
    classDef route fill:#ecfeff,stroke:#0891b2,color:#164e63;
    classDef next fill:#fef3c7,stroke:#d97706,color:#7c2d12;
    subgraph pressure["Start Here When You Need To Know"]
        direction TB
        q1["how bijux-canon-runtime is installed, run, diagnosed, and released in practice"]
        q2["which checked-in files and tests anchor the operational story"]
        q3["where a maintainer should look first when the package behaves differently"]
    end
    subgraph outcomes["This Page Should Clarify"]
        direction TB
        dest1["repeat workflows"]
        dest2["find diagnostics"]
        dest3["release safely"]
    end
    subgraph next_steps["Move Next To The Strongest Follow-up"]
        direction TB
        next1["move to interfaces when the operational path depends on a specific surface contract"]
        next2["move to quality when the question becomes whether the workflow is sufficiently proven"]
        next3["move back to architecture when operational complexity suggests a structural problem"]
    end
    context --> page
    q1 --> page
    q2 --> page
    q3 --> page
    page --> dest1
    page --> dest2
    page --> dest3
    page --> follow
    follow --> next1
    follow --> next2
    follow --> next3
    class context context;
    class page page;
    class q1,q2,q3 route;
    class dest1,dest2,dest3 route;
    class next1,next2,next3 next;
```

```mermaid
flowchart TB
    promise["Local Development<br/>clarifies: repeat workflows | find diagnostics | release safely"]
    classDef promise fill:#dbeafe,stroke:#1d4ed8,color:#1e3a8a,stroke-width:2px;
    classDef driver fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef constraint fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef ground fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    focus1["Workflow anchors"]
    focus1 --> promise
    promise --> focus1
    focus1_1["packages/bijux-canon-runtime/pyproject.toml"]
    focus1 --> focus1_1
    focus1_2["CLI entrypoint in src/bijux_canon_runtime/interfaces/cli/entrypoint.py"]
    focus1 --> focus1_2
    focus1_3["HTTP app in src/bijux_canon_runtime/api/v1"]
    focus1 --> focus1_3
    class focus1 ground;
    class focus1_1,focus1_2,focus1_3 ground;
    focus2["Operational evidence"]
    focus2 --> promise
    promise --> focus2
    focus2_1["tests/unit for api, contracts, core, interfaces, model, and runtime"]
    focus2 --> focus2_1
    focus2_2["tests/e2e for governed flow behavior"]
    focus2 --> focus2_2
    focus2_3["tests/regression and tests/smoke for replay and storage protection"]
    focus2 --> focus2_3
    class focus2 ground;
    class focus2_1,focus2_2,focus2_3 ground;
    focus3["Release pressure"]
    focus3 -.keeps the page honest.-> promise
    focus3_1["README.md"]
    focus3_1 --> focus3
    focus3_2["CHANGELOG.md"]
    focus3_2 --> focus3
    focus3_3["pyproject.toml"]
    focus3_3 --> focus3
    class focus3 constraint;
    class focus3_1,focus3_2,focus3_3 constraint;
    class promise promise;
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

## Use This Page When

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

This page explains how `bijux-canon-runtime` is expected to be operated, but it does not replace package metadata, actual runtime behavior, or validation in a real environment. A workflow is only trustworthy if a maintainer can still repeat it from the checked-in assets named here.

## Next Checks

- move to interfaces when the operational path depends on a specific surface contract
- move to quality when the question becomes whether the workflow is sufficiently proven
- move back to architecture when operational complexity suggests a structural problem

## Purpose

This page records the package-local development posture.

## Stability

Keep it aligned with the actual test layout and maintenance workflow.
