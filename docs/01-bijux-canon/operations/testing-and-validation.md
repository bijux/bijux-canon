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

## Visual Summary

```mermaid
flowchart LR
    change["Shared or cross-package change"]
    package["Run package-local proof first"]
    root["Run root checks for shared surfaces"]
    review["Keep docs, schemas, and tests aligned"]
    change --> package --> root --> review
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class change page;
    class package positive;
    class root anchor;
    class review action;
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

## Open This Page When

- you are dealing with repository-wide seams rather than one package alone
- you need shared workflow, schema, or governance context before changing code
- you want the monorepo view that sits above the package handbooks

## Decision Rule

Open this page when validation spans package boundaries, schemas, docs, or
release conventions. If the answer depends mostly on one package's local test
behavior, move back to that package handbook instead.

## What You Can Resolve Here

- which validation layers belong to packages and which belong to the repository
- which shared assets or workflows deserve inspection
- how repository proof differs from package-local proof

## Review Focus

- compare the page claims with the real root files, workflows, or schema assets
- check that repository guidance still stops where package ownership begins
- confirm that any repository rule described here is still enforceable in code or automation

## Limits

Repository guidance here does not replace executable proof. The real backstops
are the referenced files, workflows, schemas, and checks.

## Read Next

- open the owning package docs when the question stops being repository-wide
- check root files, schemas, or workflows named here before trusting prose alone
- use the maintainer handbook at `https://bijux.io/bijux-canon/07-bijux-canon-maintain/`
  when the root issue is really about automation or drift tooling

