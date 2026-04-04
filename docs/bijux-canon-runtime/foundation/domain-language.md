---
title: Domain Language
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-04-04
---

# Domain Language

The language around `bijux-canon-runtime` should reinforce the real package
boundary. Good names shorten review. Weak names force people to keep asking
whether they are looking at local behavior or at something owned elsewhere.

This page keeps the package vocabulary stable enough that docs, code, commit
messages, and review conversations can describe the same idea without drift.

Treat the foundation pages for `bijux-canon-runtime` as the package's durable self-description. If the package still feels blurry after this section, the boundary story is not clear enough yet.

## Page Maps

```mermaid
flowchart LR
    context["bijux-canon-runtime / Foundation"]
    page["Domain Language"]
    follow["Follow the narrowest next route"]
    classDef context fill:#eef2ff,stroke:#4f46e5,color:#1e2852;
    classDef page fill:#e0e7ff,stroke:#3730a3,color:#1e2852,stroke-width:2px;
    classDef route fill:#ecfeff,stroke:#0891b2,color:#164e63;
    classDef next fill:#fef3c7,stroke:#d97706,color:#7c2d12;
    subgraph pressure["Start Here When You Need To Know"]
        direction TB
        q1["what problem bijux-canon-runtime is supposed to own on purpose"]
        q2["where the package boundary stops, even when nearby code looks tempting"]
        q3["which neighboring package seams deserve comparison before the boundary is changed"]
    end
    subgraph outcomes["This Page Should Clarify"]
        direction TB
        dest1["own the right work"]
        dest2["name the boundary"]
        dest3["compare neighbors"]
    end
    subgraph next_steps["Move Next To The Strongest Follow-up"]
        direction TB
        next1["move to architecture when the question becomes structural rather than boundary-oriented"]
        next2["move to interfaces when the question becomes contract-facing"]
        next3["move to quality when the question becomes proof or review sufficiency"]
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
    promise["Domain Language<br/>clarifies: own the right work | name the boundary | compare neighbors"]
    classDef promise fill:#dbeafe,stroke:#1d4ed8,color:#1e3a8a,stroke-width:2px;
    classDef driver fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef constraint fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef ground fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    focus1["Owned here"]
    focus1 --> promise
    focus1_1["flow execution authority"]
    focus1_1 --> focus1
    focus1_2["replay and acceptability semantics"]
    focus1_2 --> focus1
    focus1_3["trace capture, runtime persistence, and execution-store behavior"]
    focus1_3 --> focus1
    class focus1 driver;
    class focus1_1,focus1_2,focus1_3 driver;
    focus2["Not owned here"]
    focus2 -.keeps the page honest.-> promise
    focus2_1["agent composition policy"]
    focus2_1 --> focus2
    focus2_2["ingest and index domain ownership"]
    focus2_2 --> focus2
    focus2_3["repository tooling and release support"]
    focus2_3 --> focus2
    class focus2 constraint;
    class focus2_1,focus2_2,focus2_3 constraint;
    focus3["Proof anchors"]
    focus3 --> promise
    promise --> focus3
    focus3_1["packages/bijux-canon-runtime"]
    focus3 --> focus3_1
    focus3_2["packages/bijux-canon-runtime/src/bijux_canon_runtime"]
    focus3 --> focus3_2
    focus3_3["packages/bijux-canon-runtime/tests"]
    focus3 --> focus3_3
    class focus3 ground;
    class focus3_1,focus3_2,focus3_3 ground;
    class promise promise;
```

## Package Vocabulary Anchors

- package name: `bijux-canon-runtime`
- Python import root: `bijux_canon_runtime`
- owning package directory: `packages/bijux-canon-runtime`
- key outputs: execution store records, replay decision artifacts, non-determinism policy evaluations

## Concrete Anchors

- `packages/bijux-canon-runtime` as the package root
- `packages/bijux-canon-runtime/src/bijux_canon_runtime` as the import boundary
- `packages/bijux-canon-runtime/tests` as the package proof surface

## Use This Page When

- you need the package idea before the implementation detail
- you are deciding whether work belongs here or in a neighboring package
- you want the shortest honest explanation of what this package is for

## Decision Rule

Use `Domain Language` to decide whether a change makes `bijux-canon-runtime` easier or harder to defend as one distinct role in the overall system. If the work makes the package broader without making its role clearer, stop and re-check the boundary before treating the change as a local improvement.

## What This Page Answers

- what problem `bijux-canon-runtime` is supposed to own on purpose
- where the package boundary stops, even when nearby code looks tempting
- which neighboring package seams deserve comparison before the boundary is changed

## Reviewer Lens

- compare the stated boundary with the modules, artifacts, and tests that are supposed to uphold it
- check that out-of-scope behavior is not quietly re-entering through convenience paths
- confirm that the package story still matches the real repository layout and neighboring package docs

## Honesty Boundary

This page can explain the intended boundary of `bijux-canon-runtime`, but it cannot prove that boundary by itself. The real proof still lives in the code, tests, and neighboring package seams that either support or contradict the story told here.

## Next Checks

- move to architecture when the question becomes structural rather than boundary-oriented
- move to interfaces when the question becomes contract-facing
- move to quality when the question becomes proof or review sufficiency

## Purpose

This page records the naming anchors that should stay stable in docs, code, and review discussions.

## Stability

Keep it aligned with the package's real import names, directories, and artifact nouns.
