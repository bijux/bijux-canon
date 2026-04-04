---
title: Workspace Layout
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-04
---

# Workspace Layout

The repository layout is intentionally direct so maintainers can see where a
concern belongs before they open any code. The directory tree is part of the
design language: it should reinforce the package split instead of making it
harder to see.

These repository pages should explain the cross-package frame that no single package can explain alone. They are strongest when they make the monorepo easier to understand without turning the root into a second owner of package behavior.

## Page Maps

```mermaid
flowchart LR
    context["bijux-canon / Repository Handbook"]
    page["Workspace Layout"]
    follow["Follow the narrowest next route"]
    classDef context fill:#eef2ff,stroke:#4f46e5,color:#1e2852;
    classDef page fill:#e0e7ff,stroke:#3730a3,color:#1e2852,stroke-width:2px;
    classDef route fill:#ecfeff,stroke:#0891b2,color:#164e63;
    classDef next fill:#fef3c7,stroke:#d97706,color:#7c2d12;
    subgraph pressure["Start Here When You Need To Know"]
        direction TB
        q1["which repository-level decision this page clarifies"]
        q2["which shared assets or workflows a reviewer should inspect"]
        q3["how the repository boundary differs from package-local ownership"]
    end
    subgraph outcomes["This Page Should Clarify"]
        direction TB
        dest1["see directory intent"]
        dest2["place work quickly"]
        dest3["separate root from package"]
    end
    subgraph next_steps["Move Next To The Strongest Follow-up"]
        direction TB
        next1["move to the owning package docs when the question stops being repository-wide"]
        next2["check root files, schemas, or workflows named here before trusting prose alone"]
        next3["use maintainer docs next if the root issue is really about automation or drift tooling"]
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
    promise["Workspace Layout<br/>clarifies: see directory intent | place work quickly | separate root from package"]
    classDef promise fill:#dbeafe,stroke:#1d4ed8,color:#1e3a8a,stroke-width:2px;
    classDef driver fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef constraint fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef ground fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    focus1["Product roots"]
    focus1 --> promise
    focus1_1["packages/"]
    focus1_1 --> focus1
    focus1_2["apis/"]
    focus1_2 --> focus1
    focus1_3["publishable package seams"]
    focus1_3 --> focus1
    class focus1 driver;
    class focus1_1,focus1_2,focus1_3 driver;
    focus2["Repository roots"]
    focus2 -.sharpens the decision.-> promise
    focus2_1["docs/"]
    focus2_1 --> focus2
    focus2_2["Makefile and makes/"]
    focus2_2 --> focus2
    focus2_3["shared workspace automation"]
    focus2_3 --> focus2
    class focus2 constraint;
    class focus2_1,focus2_2,focus2_3 constraint;
    focus3["Review outcome"]
    focus3 --> promise
    promise --> focus3
    focus3_1["place the concern"]
    focus3 --> focus3_1
    focus3_2["avoid root sprawl"]
    focus3 --> focus3_2
    focus3_3["keep ownership visible in the tree"]
    focus3 --> focus3_3
    class focus3 ground;
    class focus3_1,focus3_2,focus3_3 ground;
    class promise promise;
```

## Top-Level Directories

- `packages/` for publishable Python distributions
- `apis/` for shared schema sources and pinned artifacts
- `docs/` for the canonical handbook
- `makes/` and `Makefile` for workspace automation
- `artifacts/` for generated or checked validation outputs
- `configs/` for root-managed tool configuration

## Layout Rule

A concern should live at the root only when it serves more than one package or
when it is about the workspace itself.

## Concrete Anchors

- `pyproject.toml` for workspace metadata and commit conventions
- `Makefile` and `makes/` for root automation
- `apis/` and `.github/workflows/` for schema and validation review

## Use This Page When

- you are dealing with repository-wide seams rather than one package alone
- you need shared workflow, schema, or governance context before changing code
- you want the monorepo view that sits above the package handbooks

## Decision Rule

Use `Workspace Layout` to decide whether the current question is genuinely repository-wide or whether it belongs back in one package handbook. If the answer depends mostly on one package's local behavior, this page should redirect instead of absorbing detail that the package should own.

## What This Page Answers

- which repository-level decision this page clarifies
- which shared assets or workflows a reviewer should inspect
- how the repository boundary differs from package-local ownership

## Reviewer Lens

- compare the page claims with the real root files, workflows, or schema assets
- check that repository guidance still stops where package ownership begins
- confirm that any repository rule described here is still enforceable in code or automation

## Honesty Boundary

These pages explain repository-level intent and shared rules, but they do not override package-local ownership. They also do not count as proof by themselves; the real backstops are the referenced files, workflows, schemas, and checks.

## Next Checks

- move to the owning package docs when the question stops being repository-wide
- check root files, schemas, or workflows named here before trusting prose alone
- use maintainer docs next if the root issue is really about automation or drift tooling

## Purpose

This page provides the shortest file-system map for the repository.

## Stability

Keep this page aligned with the real root directories and remove any mention of retired roots.
