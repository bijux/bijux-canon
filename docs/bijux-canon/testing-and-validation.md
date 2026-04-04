---
title: Testing and Validation
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-04
---

# Testing and Validation

Validation in `bijux-canon` is layered: packages protect their own behavior,
while the repository protects the seams between packages, schemas, docs, and
release conventions.

This distinction is essential for credibility. The repository should never ask
readers to trust prose alone. If a rule matters, some checked-in package test,
drift check, or CI workflow should be able to notice when it stops being true.

The deeper reason for this layout is that trust has to be local before it can
be global. Each package proves its own promises first. The repository then
proves that the packages still fit together honestly.

These repository pages should explain the cross-package frame that no single package can explain alone. They are strongest when they make the monorepo easier to understand without turning the root into a second owner of package behavior.

## Page Maps

```mermaid
flowchart LR
    context["bijux-canon / Repository Handbook"]
    page["Testing and Validation"]
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
        dest1["see proof layers"]
        dest2["separate package from repository"]
        dest3["trace trust backstops"]
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
    promise["Testing and Validation<br/>clarifies: see proof layers | separate package from repository | trace trust backstops"]
    classDef promise fill:#dbeafe,stroke:#1d4ed8,color:#1e3a8a,stroke-width:2px;
    classDef driver fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef constraint fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef ground fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    focus1["Package proof"]
    focus1 --> promise
    promise --> focus1
    focus1_1["unit to invariants"]
    focus1 --> focus1_1
    focus1_2["package-local contracts"]
    focus1 --> focus1_2
    focus1_3["behavior defended where it lives"]
    focus1 --> focus1_3
    class focus1 ground;
    class focus1_1,focus1_2,focus1_3 ground;
    focus2["Repository proof"]
    focus2 --> promise
    promise --> focus2
    focus2_1["schema drift"]
    focus2 --> focus2_1
    focus2_2["CI workflows"]
    focus2 --> focus2_2
    focus2_3["workspace-level regression backstops"]
    focus2 --> focus2_3
    class focus2 ground;
    class focus2_1,focus2_2,focus2_3 ground;
    focus3["Reader outcome"]
    focus3 --> promise
    promise --> focus3
    focus3_1["trust locally first"]
    focus3 --> focus3_1
    focus3_2["then trust the full fit"]
    focus3 --> focus3_2
    focus3_3["see where proof should start and where it should escalate"]
    focus3 --> focus3_3
    class focus3 ground;
    class focus3_1,focus3_2,focus3_3 ground;
    class promise promise;
```

## Validation Layers

- package-local unit, integration, e2e, and invariant suites
- schema drift and packaging checks in `bijux-canon-dev`
- repository CI workflows under `.github/workflows/`

## Validation Rule

A prose promise is incomplete until either package tests or repository tooling
can detect its drift.

## Concrete Anchors

- `pyproject.toml` for workspace metadata and commit conventions
- `Makefile` and `makes/` for root automation
- `apis/` and `.github/workflows/` for schema and validation review

## Use This Page When

- you are dealing with repository-wide seams rather than one package alone
- you need shared workflow, schema, or governance context before changing code
- you want the monorepo view that sits above the package handbooks

## Decision Rule

Use `Testing and Validation` to decide whether the current question is genuinely repository-wide or whether it belongs back in one package handbook. If the answer depends mostly on one package's local behavior, this page should redirect instead of absorbing detail that the package should own.

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

This page explains the relationship between package truth and repository truth.

## Stability

Keep it aligned with the current test layout and CI workflows instead of aspirational future checks.
