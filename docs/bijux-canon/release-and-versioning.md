---
title: Release and Versioning
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-04
---

# Release and Versioning

The repository uses commitizen for conventional commit messages and package
tags for version discovery through Hatch VCS. Version resolution is therefore
both a repository concern and a package concern.

The wording of the commit history matters here because the repository is meant
to stay understandable years later. A good commit message should explain
durable intent, not just what happened to be touched in one diff.

These repository pages should explain the cross-package frame that no single package can explain alone. They are strongest when they make the monorepo easier to understand without turning the root into a second owner of package behavior.

## Page Maps

```mermaid
flowchart LR
    context["bijux-canon / Repository Handbook"]
    page["Release and Versioning"]
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
        dest1["see release mechanics"]
        dest2["see package-version link"]
        dest3["understand commit history role"]
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
    promise["Release and Versioning<br/>clarifies: see release mechanics | see package-version link | understand commit history role"]
    classDef promise fill:#dbeafe,stroke:#1d4ed8,color:#1e3a8a,stroke-width:2px;
    classDef driver fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef constraint fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef ground fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    focus1["Repository rules"]
    focus1 --> promise
    focus1_1["commitizen"]
    focus1_1 --> focus1
    focus1_2["tag conventions"]
    focus1_2 --> focus1
    focus1_3["durable commit intent"]
    focus1_3 --> focus1
    class focus1 driver;
    class focus1_1,focus1_2,focus1_3 driver;
    focus2["Package mechanics"]
    focus2 -.sharpens the decision.-> promise
    focus2_1["_version.py"]
    focus2_1 --> focus2
    focus2_2["package metadata"]
    focus2_2 --> focus2
    focus2_3["release artifacts move with code"]
    focus2_3 --> focus2
    class focus2 constraint;
    class focus2_1,focus2_2,focus2_3 constraint;
    focus3["Reader outcome"]
    focus3 --> promise
    promise --> focus3
    focus3_1["understand version movement"]
    focus3 --> focus3_1
    focus3_2["read durable intent"]
    focus3 --> focus3_2
    focus3_3["see what changed at package versus workspace level"]
    focus3 --> focus3_3
    class focus3 ground;
    class focus3_1,focus3_2,focus3_3 ground;
    class promise promise;
```

## Shared Release Facts

- root commit rules live in `pyproject.toml`
- package versions are written to package-local `_version.py` files by Hatch VCS
- release support helpers live in `bijux-canon-dev`

## Versioning Rule

Commit messages should communicate long-lived intent clearly enough that a
maintainer can understand them years later without opening the diff first.

## Concrete Anchors

- `pyproject.toml` for workspace metadata and commit conventions
- `Makefile` and `makes/` for root automation
- `apis/` and `.github/workflows/` for schema and validation review

## Use This Page When

- you are dealing with repository-wide seams rather than one package alone
- you need shared workflow, schema, or governance context before changing code
- you want the monorepo view that sits above the package handbooks

## Decision Rule

Use `Release and Versioning` to decide whether the current question is genuinely repository-wide or whether it belongs back in one package handbook. If the answer depends mostly on one package's local behavior, this page should redirect instead of absorbing detail that the package should own.

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

This page connects the root commit conventions to the package release mechanism.

## Stability

Keep this page aligned with the release tooling that is actually configured in the repository.
