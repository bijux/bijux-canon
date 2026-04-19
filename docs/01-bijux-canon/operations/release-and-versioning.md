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

## Visual Summary

```mermaid
flowchart TB
    page["Release and Versioning<br/>clarifies: see release mechanics | see package-version link | understand commit history role"]
    classDef page fill:#dbeafe,stroke:#1d4ed8,color:#1e3a8a,stroke-width:2px;
    classDef positive fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef caution fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef anchor fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    classDef action fill:#fef3c7,stroke:#d97706,color:#7c2d12;
    detail1["commitizen"]
    detail1 --> page
    detail2["tag conventions"]
    detail2 -.gives the reader orientation.-> page
    detail3["durable commit intent"]
    detail3 --> page
    detail4["_version.py"]
    detail4 -.gives the reader orientation.-> page
    detail5["package metadata"]
    detail5 --> page
    detail6["release artifacts move with code"]
    detail6 -.gives the reader orientation.-> page
    detail7["understand version movement"]
    detail7 --> page
    detail8["read durable intent"]
    detail8 -.gives the reader orientation.-> page
    detail9["see what changed at package versus workspace level"]
    detail9 --> page
    next1["schemas"]
    page --> next1
    next2["maintainer docs"]
    page --> next2
    next3["owning package docs"]
    page --> next3
    class page page;
    class detail1,detail2,detail3,detail4,detail5,detail6,detail7,detail8,detail9 anchor;
    class next1,next2,next3 action;
```

## Shared Release Facts

- root commit rules live in `pyproject.toml`
- package versions are written to package-local `_version.py` files by Hatch VCS
- release support helpers live in `bijux-canon-dev`
- the split release workflows (`release-pypi.yml`, `release-ghcr.yml`, `release-github.yml`) publish package artifacts and release metadata

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
