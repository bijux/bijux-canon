---
title: SBOM and Supply Chain
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-04
---

# SBOM and Supply Chain

Supply-chain visibility is a repository maintenance concern, so SBOM helpers
live in `bijux-canon-dev` instead of being duplicated by each package.

The point is not just compliance. The point is to keep dependency and build
provenance explainable at repository level without smearing that burden
across every product package.

These maintainer pages should read like explicit operational memory for repository-health work. They are strongest when they expose automation intent, package impact, and repository policy without pretending that CI logs are documentation.

## Page Maps

```mermaid
flowchart LR
    context["bijux-canon / Maintainer Handbook"]
    page["SBOM and Supply Chain"]
    follow["Follow the narrowest next route"]
    classDef context fill:#eef2ff,stroke:#4f46e5,color:#1e2852;
    classDef page fill:#e0e7ff,stroke:#3730a3,color:#1e2852,stroke-width:2px;
    classDef route fill:#ecfeff,stroke:#0891b2,color:#164e63;
    classDef next fill:#fef3c7,stroke:#d97706,color:#7c2d12;
    subgraph pressure["Start Here When You Need To Know"]
        direction TB
        q1["which repository maintenance concern this page explains"]
        q2["which maintainer modules or tests support that concern"]
        q3["what a reviewer should confirm before changing repository automation"]
    end
    subgraph outcomes["This Page Should Clarify"]
        direction TB
        dest1["explain automation"]
        dest2["see repository-health scope"]
        dest3["review package impact"]
    end
    subgraph next_steps["Move Next To The Strongest Follow-up"]
        direction TB
        next1["move to product package docs if the question is user-facing behavior rather than repository health"]
        next2["open the relevant helper module or test after using this page to orient yourself"]
        next3["return to repository handbook pages when the maintainer issue turns out to be root policy instead"]
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
    promise["SBOM and Supply Chain<br/>clarifies: explain automation | see repository-health scope | review package impact"]
    classDef promise fill:#dbeafe,stroke:#1d4ed8,color:#1e3a8a,stroke-width:2px;
    classDef driver fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef constraint fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef ground fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    focus1["Maintainer role"]
    focus1 --> promise
    focus1_1["quality gates"]
    focus1_1 --> focus1
    focus1_2["security gates"]
    focus1_2 --> focus1
    focus1_3["release support"]
    focus1_3 --> focus1
    class focus1 driver;
    class focus1_1,focus1_2,focus1_3 driver;
    focus2["Repository health"]
    focus2 -.sharpens the decision.-> promise
    focus2_1["schema integrity"]
    focus2_1 --> focus2
    focus2_2["supply-chain visibility"]
    focus2_2 --> focus2
    focus2_3["package-aware automation"]
    focus2_3 --> focus2
    class focus2 constraint;
    class focus2_1,focus2_2,focus2_3 constraint;
    focus3["Operational outcome"]
    focus3 --> promise
    promise --> focus3
    focus3_1["release clarity"]
    focus3 --> focus3_1
    focus3_2["package consistency"]
    focus3 --> focus3_2
    focus3_3["less CI archaeology"]
    focus3 --> focus3_3
    class focus3 ground;
    class focus3_1,focus3_2,focus3_3 ground;
    class promise promise;
```

## Current Surfaces

- `sbom/requirements_writer.py`
- `tests/test_sbom_requirements_writer.py`
- shared dependency metadata in package `pyproject.toml` files

## Concrete Anchors

- `packages/bijux-canon-dev/src/bijux_canon_dev` for maintainer helpers
- `packages/bijux-canon-dev/tests` for executable maintenance proof
- `apis/` and root workflows for repository-level integration points

## Use This Page When

- you are changing repository automation, validation, or release support
- you need maintainer-only context that should not live in product package docs
- you are reviewing CI, schema drift, or supply-chain behavior

## Decision Rule

Use `SBOM and Supply Chain` to decide whether a change belongs to maintainer automation or to a product package contract. If the change would affect end-user behavior directly, this page should push the review back toward the owning product package instead of letting maintainer scope sprawl.

## What This Page Answers

- which repository maintenance concern this page explains
- which maintainer modules or tests support that concern
- what a reviewer should confirm before changing repository automation

## Reviewer Lens

- compare the described maintainer behavior with the actual helper modules and tests
- check that maintainer-only guidance has not leaked into product-facing pages
- confirm that repository automation still names its package impact explicitly

## Next Checks

- move to product package docs if the question is user-facing behavior rather than repository health
- open the relevant helper module or test after using this page to orient yourself
- return to repository handbook pages when the maintainer issue turns out to be root policy instead

## Honesty Boundary

This section can describe maintainer automation and repository health work, but it should never imply that maintainer tooling is part of the end-user product surface. It also should not pretend that hidden scripts count as documentation just because CI happens to run them.

## Purpose

This page explains the home for supply-chain oriented repository tooling.

## Stability

Keep it aligned with the checked-in SBOM helpers and tests.
