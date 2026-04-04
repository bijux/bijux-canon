---
title: Interfaces
audience: mixed
type: index
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-04-04
---

# Interfaces

This section explains which commands, APIs, imports, schemas, and artifacts `bijux-canon-index` is prepared to stand behind as real surfaces.

These pages explain the public face of `bijux-canon-index`. They help a caller separate deliberate contracts from incidental visibility before a dependency hardens around the wrong surface.

Treat the interfaces pages for `bijux-canon-index` as the bridge between implementation detail and caller expectation. They should show what the package is prepared to defend before a dependency forms.

## Page Maps

```mermaid
flowchart LR
    context["bijux-canon-index / Interfaces"]
    page["Interfaces"]
    follow["Follow the narrowest next route"]
    classDef context fill:#eef2ff,stroke:#4f46e5,color:#1e2852;
    classDef page fill:#e0e7ff,stroke:#3730a3,color:#1e2852,stroke-width:2px;
    classDef route fill:#ecfeff,stroke:#0891b2,color:#164e63;
    classDef next fill:#fef3c7,stroke:#d97706,color:#7c2d12;
    subgraph pressure["Start Here When You Need To Know"]
        direction TB
        q1["which public or operator-facing surfaces bijux-canon-index is really asking readers to trust"]
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
    promise["Interfaces<br/>clarifies: identify contracts | see caller impact | review compatibility"]
    classDef promise fill:#dbeafe,stroke:#1d4ed8,color:#1e3a8a,stroke-width:2px;
    classDef driver fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef constraint fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef ground fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    focus1["Caller surfaces"]
    focus1 --> promise
    promise --> focus1
    focus1_1["CLI modules under src/bijux_canon_index/interfaces/cli"]
    focus1 --> focus1_1
    focus1_2["HTTP app under src/bijux_canon_index/api"]
    focus1 --> focus1_2
    focus1_3["OpenAPI schema files under apis/bijux-canon-index/v1"]
    focus1 --> focus1_3
    class focus1 ground;
    class focus1_1,focus1_2,focus1_3 ground;
    focus2["Contract evidence"]
    focus2 --> promise
    promise --> focus2
    focus2_1["apis/bijux-canon-index/v1/schema.yaml"]
    focus2 --> focus2_1
    focus2_2["apis/bijux-canon-index/v1/openapi.v1.json"]
    focus2 --> focus2_2
    focus2_3["vector execution result collections"]
    focus2 --> focus2_3
    class focus2 ground;
    class focus2_1,focus2_2,focus2_3 ground;
    focus3["Review pressure"]
    focus3 -.keeps the page honest.-> promise
    focus3_1["tests/unit for API, application, contracts, domain, infra, and tooling"]
    focus3_1 --> focus3
    focus3_2["tests/e2e for CLI workflows, API smoke, determinism gates, and provenance gates"]
    focus3_2 --> focus3
    focus3_3["tests/conformance and tests/compat_v01 for compatibility behavior"]
    focus3_3 --> focus3
    class focus3 constraint;
    class focus3_1,focus3_2,focus3_3 constraint;
    class promise promise;
```

## Pages in This Section

- [CLI Surface](cli-surface.md)
- [API Surface](api-surface.md)
- [Configuration Surface](configuration-surface.md)
- [Data Contracts](data-contracts.md)
- [Artifact Contracts](artifact-contracts.md)
- [Entrypoints and Examples](entrypoints-and-examples.md)
- [Operator Workflows](operator-workflows.md)
- [Public Imports](public-imports.md)
- [Compatibility Commitments](compatibility-commitments.md)

## Read Across the Package

- [Foundation](../foundation/index.md) when you need the package boundary and ownership story first
- [Architecture](../architecture/index.md) when the question becomes structural, modular, or execution-oriented
- [Operations](../operations/index.md) when the question becomes procedural, environmental, diagnostic, or release-oriented
- [Quality](../quality/index.md) when the question becomes proof, risk, trust, or review sufficiency

## Concrete Anchors

- CLI modules under src/bijux_canon_index/interfaces/cli
- HTTP app under src/bijux_canon_index/api
- OpenAPI schema files under apis/bijux-canon-index/v1
- apis/bijux-canon-index/v1/schema.yaml

## Use This Page When

- you need the public command, API, import, schema, or artifact surface
- you are checking whether a caller can safely rely on a given entrypoint or shape
- you want the contract-facing side of the package before building on it

## Decision Rule

Use `Interfaces` to decide whether a caller-facing surface is explicit enough to depend on. If the surface cannot be tied back to concrete code, schemas, artifacts, examples, and tests, treat it as unstable until that evidence is visible.

## What This Page Answers

- which public or operator-facing surfaces `bijux-canon-index` is really asking readers to trust
- which schemas, artifacts, imports, or commands behave like contracts
- what compatibility pressure a change to this surface would create

## Reviewer Lens

- compare commands, schemas, imports, and artifacts against the documented surface one by one
- check whether a seemingly local change actually needs compatibility review
- confirm that examples still point to real entrypoints and not to stale habits

## Honesty Boundary

This page can identify the intended public surfaces of `bijux-canon-index`, but real compatibility depends on code, schemas, artifacts, examples, and tests staying aligned. If those disagree, the prose is wrong or incomplete.

## Next Checks

- move to operations when the caller-facing question becomes procedural or environmental
- move to quality when compatibility or evidence of protection becomes the real issue
- move back to architecture when a public-surface question reveals a deeper structural drift

## Purpose

This page explains how to use the interfaces section for `bijux-canon-index` without repeating the detail that belongs on the topic pages beneath it.

## Stability

This page is part of the canonical package docs spine. Keep it aligned with the current package boundary and the topic pages in this section.
