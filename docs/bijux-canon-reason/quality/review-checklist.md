---
title: Review Checklist
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# Review Checklist

Reviewing changes in `bijux-canon-reason` should include both behavior and documentation.

The checklist is not here to slow people down with ceremony. It is here to stop
fast review from becoming shallow review when a change touches boundaries,
contracts, or proof.

Treat the quality pages for `bijux-canon-reason` as the proof frame around the package. They should show how trust is earned and where skepticism still belongs.

## Page Maps

```mermaid
flowchart LR
    context["bijux-canon-reason / Quality"]
    page["Review Checklist"]
    follow["Follow the narrowest next route"]
    classDef context fill:#eef2ff,stroke:#4f46e5,color:#1e2852;
    classDef page fill:#e0e7ff,stroke:#3730a3,color:#1e2852,stroke-width:2px;
    classDef route fill:#ecfeff,stroke:#0891b2,color:#164e63;
    classDef next fill:#fef3c7,stroke:#d97706,color:#7c2d12;
    subgraph pressure["Start Here When You Need To Know"]
        direction TB
        q1["what currently proves the bijux-canon-reason contract instead of merely describing it"]
        q2["which risks, limits, and assumptions still need explicit skepticism"]
        q3["what a reviewer should be able to say before accepting a change as done"]
    end
    subgraph outcomes["This Page Should Clarify"]
        direction TB
        dest1["see proof"]
        dest2["see limitations"]
        dest3["judge done-ness"]
    end
    subgraph next_steps["Move Next To The Strongest Follow-up"]
        direction TB
        next1["move to foundation when the risk appears to be boundary confusion rather than missing tests"]
        next2["move to architecture when the proof gap points to structural drift"]
        next3["move to interfaces or operations when the proof question is really about a contract or workflow"]
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
    promise["Review Checklist<br/>clarifies: see proof | see limitations | judge done-ness"]
    classDef promise fill:#dbeafe,stroke:#1d4ed8,color:#1e3a8a,stroke-width:2px;
    classDef driver fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef constraint fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef ground fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    focus1["Proof surfaces"]
    focus1 --> promise
    promise --> focus1
    focus1_1["tests/unit for planning, reasoning, execution, verification, and interfaces"]
    focus1 --> focus1_1
    focus1_2["tests/e2e for API, CLI, replay gates, retrieval reasoning, and smoke coverage"]
    focus1 --> focus1_2
    focus1_3["tests/perf for retrieval benchmark coverage"]
    focus1 --> focus1_3
    class focus1 ground;
    class focus1_1,focus1_2,focus1_3 ground;
    focus2["Risk anchors"]
    focus2 -.keeps the page honest.-> promise
    focus2_1["README.md"]
    focus2_1 --> focus2
    focus2_2["CHANGELOG.md"]
    focus2_2 --> focus2
    focus2_3["pyproject.toml"]
    focus2_3 --> focus2
    class focus2 constraint;
    class focus2_1,focus2_2,focus2_3 constraint;
    focus3["Review bar"]
    focus3 --> promise
    promise --> focus3
    focus3_1["package trust after change"]
    focus3 --> focus3_1
    focus3_2["proof before confidence"]
    focus3 --> focus3_2
    focus3_3["done means defended behavior"]
    focus3 --> focus3_3
    class focus3 ground;
    class focus3_1,focus3_2,focus3_3 ground;
    class promise promise;
```

## Checklist

- did ownership stay inside the correct package boundary
- do interface or artifact changes have matching docs and tests
- are filenames, commit messages, and symbols still clear enough to age well

## Concrete Anchors

- tests/unit for planning, reasoning, execution, verification, and interfaces
- tests/e2e for API, CLI, replay gates, retrieval reasoning, and smoke coverage
- README.md

## Use This Page When

- you are reviewing tests, invariants, limitations, or ongoing risks
- you need evidence that the documented contract is actually defended
- you are deciding whether a change is truly done rather than merely implemented

## Decision Rule

Use `Review Checklist` to decide whether `bijux-canon-reason` has actually earned trust after a change. If one narrow green check hides a wider contract, risk, or validation gap, the work is not done yet.

## What This Page Answers

- what currently proves the `bijux-canon-reason` contract instead of merely describing it
- which risks, limits, and assumptions still need explicit skepticism
- what a reviewer should be able to say before accepting a change as done

## Reviewer Lens

- compare the documented proof story with the actual test layout and release posture
- look for limitations or risks that should have moved with recent behavior changes
- verify that the claimed done-ness standard still reflects real validation practice

## Honesty Boundary

This page explains how `bijux-canon-reason` is supposed to earn trust, but it does not claim that prose alone is enough. If the listed tests, checks, and review practice stop backing the story, the story has to change.

## Next Checks

- move to foundation when the risk appears to be boundary confusion rather than missing tests
- move to architecture when the proof gap points to structural drift
- move to interfaces or operations when the proof question is really about a contract or workflow

## Purpose

This page records a compact review lens for package changes.

## Stability

Update it only when the package review posture genuinely changes.
