---
title: Data Contracts
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-04
---

# Data Contracts

Data contracts in `bijux-canon-agent` include schemas, structured models, and any stable
payload shape that neighboring systems are expected to understand.

This page keeps data shape changes reviewable. If a record or payload matters to
another package, another process, or a replay path, it deserves to be described
as a contract rather than left implicit in implementation details.

Treat the interfaces pages for `bijux-canon-agent` as the bridge between implementation detail and caller expectation. They should show what the package is prepared to defend before a dependency forms.

## Page Maps

```mermaid
flowchart LR
    context["bijux-canon-agent / Interfaces"]
    page["Data Contracts"]
    follow["Follow the narrowest next route"]
    classDef context fill:#eef2ff,stroke:#4f46e5,color:#1e2852;
    classDef page fill:#e0e7ff,stroke:#3730a3,color:#1e2852,stroke-width:2px;
    classDef route fill:#ecfeff,stroke:#0891b2,color:#164e63;
    classDef next fill:#fef3c7,stroke:#d97706,color:#7c2d12;
    subgraph pressure["Start Here When You Need To Know"]
        direction TB
        q1["which public or operator-facing surfaces bijux-canon-agent is really asking readers to trust"]
        q2["which schemas, artifacts, imports, or commands behave like contracts"]
        q3["what compatibility pressure a change to this surface would create"]
    end
    subgraph outcomes["This Page Should Clarify"]
        direction TB
        dest1["identify contracts"]
        dest2["see caller impact"]
        dest3["review compatibility"]
    end
    subgraph next_steps["Move Next To The Strongest Follow-up"]
        direction TB
        next1["move to operations when the caller-facing question becomes procedural or environmental"]
        next2["move to quality when compatibility or evidence of protection becomes the real issue"]
        next3["move back to architecture when a public-surface question reveals a deeper structural drift"]
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
    promise["Data Contracts<br/>clarifies: identify contracts | see caller impact | review compatibility"]
    classDef promise fill:#dbeafe,stroke:#1d4ed8,color:#1e3a8a,stroke-width:2px;
    classDef driver fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef constraint fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef ground fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    focus1["Caller surfaces"]
    focus1 --> promise
    promise --> focus1
    focus1_1["CLI entrypoint in src/bijux_canon_agent/interfaces/cli/entrypoint.py"]
    focus1 --> focus1_1
    focus1_2["operator configuration under src/bijux_canon_agent/config"]
    focus1 --> focus1_2
    focus1_3["HTTP-adjacent modules under src/bijux_canon_agent/api"]
    focus1 --> focus1_3
    class focus1 ground;
    class focus1_1,focus1_2,focus1_3 ground;
    focus2["Contract evidence"]
    focus2 --> promise
    promise --> focus2
    focus2_1["apis/bijux-canon-agent/v1/schema.yaml"]
    focus2 --> focus2_1
    focus2_2["trace-backed final outputs"]
    focus2 --> focus2_2
    focus2_3["workflow graph execution records"]
    focus2 --> focus2_3
    class focus2 ground;
    class focus2_1,focus2_2,focus2_3 ground;
    focus3["Review pressure"]
    focus3 -.keeps the page honest.-> promise
    focus3_1["tests/unit for local behavior and utility coverage"]
    focus3_1 --> focus3
    focus3_2["tests/integration and tests/e2e for end-to-end workflow behavior"]
    focus3_2 --> focus3
    focus3_3["tests/invariants for package promises that should not drift"]
    focus3_3 --> focus3
    class focus3 constraint;
    class focus3_1,focus3_2,focus3_3 constraint;
    class promise promise;
```

## Contract Anchors

- apis/bijux-canon-agent/v1/schema.yaml

## Artifact Anchors

- trace-backed final outputs
- workflow graph execution records
- operator-visible result artifacts

## Concrete Anchors

- CLI entrypoint in src/bijux_canon_agent/interfaces/cli/entrypoint.py
- operator configuration under src/bijux_canon_agent/config
- HTTP-adjacent modules under src/bijux_canon_agent/api
- apis/bijux-canon-agent/v1/schema.yaml

## Use This Page When

- you need the public command, API, import, schema, or artifact surface
- you are checking whether a caller can safely rely on a given entrypoint or shape
- you want the contract-facing side of the package before building on it

## Decision Rule

Use `Data Contracts` to decide whether a caller-facing surface is explicit enough to depend on. If the surface cannot be tied back to concrete code, schemas, artifacts, examples, and tests, treat it as unstable until that evidence is visible.

## What This Page Answers

- which public or operator-facing surfaces `bijux-canon-agent` is really asking readers to trust
- which schemas, artifacts, imports, or commands behave like contracts
- what compatibility pressure a change to this surface would create

## Reviewer Lens

- compare commands, schemas, imports, and artifacts against the documented surface one by one
- check whether a seemingly local change actually needs compatibility review
- confirm that examples still point to real entrypoints and not to stale habits

## Honesty Boundary

This page can identify the intended public surfaces of `bijux-canon-agent`, but real compatibility depends on code, schemas, artifacts, examples, and tests staying aligned. If those disagree, the prose is wrong or incomplete.

## Next Checks

- move to operations when the caller-facing question becomes procedural or environmental
- move to quality when compatibility or evidence of protection becomes the real issue
- move back to architecture when a public-surface question reveals a deeper structural drift

## Purpose

This page explains which structured shapes deserve compatibility review.

## Stability

Keep it aligned with tracked schemas, stable models, and durable artifacts.
