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

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Repository Handbook"]
    section --> page["Documentation System"]
    dest1["package boundaries"]
    dest2["shared workflows"]
    dest3["reviewable decisions"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Documentation System"]
    focus1["Repository intent"]
    page --> focus1
    focus1_1["scope"]
    focus1 --> focus1_1
    focus1_2["shared ownership"]
    focus1 --> focus1_2
    focus2["Review inputs"]
    page --> focus2
    focus2_1["code"]
    focus2 --> focus2_1
    focus2_2["schemas"]
    focus2 --> focus2_2
    focus2_3["automation"]
    focus2 --> focus2_3
    focus3["Review outputs"]
    page --> focus3
    focus3_1["clear decisions"]
    focus3 --> focus3_1
    focus3_2["stable docs"]
    focus3 --> focus3_2
```

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

## What This Page Answers

- which repository-level decision this page clarifies
- which shared assets or workflows a reviewer should inspect
- how the repository boundary differs from package-local ownership

## Reviewer Lens

- compare the page claims with the real root files, workflows, or schema assets
- check that repository guidance still stops where package ownership begins
- confirm that any repository rule described here is still enforceable in code or automation

## Honesty Boundary

These pages explain repository-level intent and shared rules, but they do not override package-local ownership or serve as evidence without the referenced files, workflows, and checks.

## Purpose

This page records the handbook system itself so the structure stays intentional instead of growing ad hoc again.

## Stability

Keep this page aligned with the actual docs tree and the layout rules enforced by this documentation catalog.

## Core Claim

Each repository handbook page should make one monorepo-level decision legible enough that package-local pages do not need to reinvent root context.

## Why It Matters

Repository pages matter because they keep shared rules, schemas, workflows, and release expectations from being rediscovered separately inside each package.

## If It Drifts

- root rules become folklore instead of checked-in reference
- packages start re-explaining shared repository behavior inconsistently
- reviewers lose the ability to separate monorepo policy from package-local design

## Representative Scenario

A cross-package change touches schemas, automation, and release behavior at once. The repository page should tell the reviewer which part of that decision belongs at the root and which part belongs back in package-local docs.

## Source Of Truth Order

- root files like `pyproject.toml`, `Makefile`, `makes/`, and `.github/workflows/` for actual repository behavior
- `apis/` for tracked shared schema artifacts
- this section for the explanation of how those assets fit together
