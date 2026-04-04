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

## Page Maps

```mermaid
flowchart LR
    scope["bijux-canon"] --> section["Repository Handbook"]
    section --> page["Documentation System"]
    dest1["see handbook layout"]
    dest2["see honesty rule"]
    dest3["understand reader promise"]
    page --> dest1
    page --> dest2
    page --> dest3
```

```mermaid
flowchart TD
    page["Documentation System"]
    focus1["Structure"]
    page --> focus1
    focus1_1["root index"]
    focus1 --> focus1_1
    focus1_2["section indexes and topic pages"]
    focus1 --> focus1_2
    focus2["References"]
    page --> focus2
    focus2_1["bijux-pollenomics"]
    focus2 --> focus2_1
    focus2_2["bijux-masterclass"]
    focus2 --> focus2_2
    focus3["Reader outcome"]
    page --> focus3
    focus3_1["self-sufficient docs"]
    focus3 --> focus3_1
    focus3_2["less meeting debt"]
    focus3 --> focus3_2
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
