---
title: Documentation System
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-04
---

# Documentation System

The root documentation site is the canonical handbook for repository and
package behavior. It is intentionally structured like the reference documentation
in `bijux-pollenomics` and `bijux-masterclass`: one root index, section indexes,
and topic pages with stable names and repeated layout.

The goal is not just consistency. The goal is reader trust. The handbook
should let a new reviewer understand the design quickly, let a maintainer find
concrete anchors without guesswork, and stay honest about what the docs can
explain versus what only code and tests can prove.

A good documentation system should reduce meeting debt. If the handbook is
working, a reader can understand the whole idea of `bijux-canon`, choose the
right page, and verify the claims from checked-in assets without needing a
private walkthrough first.

These repository pages should explain the cross-package frame that no single package can explain alone. They are strongest when they make the monorepo easier to understand without turning the root into a second owner of package behavior.

## Visual Summary

```mermaid
flowchart TB
    page["Documentation System<br/>clarifies: see handbook layout | see honesty rule | understand reader promise"]
    classDef page fill:#dbeafe,stroke:#1d4ed8,color:#1e3a8a,stroke-width:2px;
    classDef positive fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef caution fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef anchor fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    classDef action fill:#fef3c7,stroke:#d97706,color:#7c2d12;
    detail1["root index"]
    detail1 --> page
    detail2["section indexes"]
    detail2 -.gives the reader orientation.-> page
    detail3["topic pages that carry proof"]
    detail3 --> page
    detail4["bijux-pollenomics"]
    detail4 -.gives the reader orientation.-> page
    detail5["bijux-masterclass"]
    detail5 --> page
    detail6["shared Bijux docs language"]
    detail6 -.gives the reader orientation.-> page
    detail7["self-sufficient docs"]
    detail7 --> page
    detail8["less meeting debt"]
    detail8 -.gives the reader orientation.-> page
    detail9["diagrams and prose that actually orient readers"]
    detail9 --> page
    next1["owning package docs"]
    page --> next1
    next2["schemas"]
    page --> next2
    next3["maintainer docs"]
    page --> next3
    class page page;
    class detail1,detail2,detail3,detail4,detail5,detail6,detail7,detail8,detail9 anchor;
    class next1,next2,next3 action;
```

## Handbook Shape

- one landing page that explains the split and routes readers quickly
- one repository handbook for cross-package rules and shared assets
- one five-category handbook per canonical product package
- one maintainer handbook for repository-health automation
- one compatibility handbook for legacy names and migration pressure

## Documentation Rules

- use stable filenames that describe durable intent
- keep package handbooks on the same five-category spine
- separate product docs, maintainer docs, and legacy-compat docs
- update docs in the same change series that changes the underlying behavior

## Concrete Anchors

- `pyproject.toml` for workspace metadata and commit conventions
- `Makefile` and `makes/` for root automation
- `apis/` and `.github/workflows/` for schema and validation review

## Use This Page When

- you are dealing with repository-wide seams rather than one package alone
- you need shared workflow, schema, or governance context before changing code
- you want the monorepo view that sits above the package handbooks

## Decision Rule

Use `Documentation System` to decide whether the current question is genuinely repository-wide or whether it belongs back in one package handbook. If the answer depends mostly on one package's local behavior, this page should redirect instead of absorbing detail that the package should own.

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

This page records the handbook system itself so the structure stays intentional instead of growing ad hoc again.

## Stability

Keep this page aligned with the actual docs tree and the layout rules enforced by this documentation catalog.
