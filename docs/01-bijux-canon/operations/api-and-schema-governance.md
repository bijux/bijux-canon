---
title: API and Schema Governance
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-04
---

# API and Schema Governance

Shared API artifacts live under `apis/` so schema review does not depend on
reading package source alone. This repository currently tracks schemas for
ingest, index, reason, agent, and runtime.

That matters because the repository wants public surfaces to be reviewable in
the open. A caller or reviewer should not need to reverse-engineer Python
modules just to understand whether an HTTP or artifact contract changed.

## Visual Summary

```mermaid
flowchart LR
    code["Code changes"]
    schema["Tracked schema in apis/"]
    checks["Drift and validation checks"]
    review["Review the contract delta"]
    code --> schema --> checks --> review
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class code page;
    class schema anchor;
    class checks positive;
    class review action;
```

## Governance Rules

- package code and tracked schema files must describe the same public behavior
- drift checks belong in `bijux-canon-dev` or package tests, not in prose alone
- schema hashes and pinned OpenAPI artifacts should move only with reviewable intent

## Current Schema Roots

- `apis/bijux-canon-agent/v1`
- `apis/bijux-canon-index/v1`
- `apis/bijux-canon-ingest/v1`
- `apis/bijux-canon-reason/v1`
- `apis/bijux-canon-runtime/v1`

## Concrete Anchors

- `pyproject.toml` for workspace metadata and commit conventions
- `Makefile` and `makes/` for root automation
- `apis/` and `.github/workflows/` for schema and validation review

## Use This Page When

- you are dealing with repository-wide seams rather than one package alone
- you need shared workflow, schema, or governance context before changing code
- you want the monorepo view that sits above the package handbooks

## Decision Rule

Use this page when a contract spans packages, schemas, and shared review
workflow. If the answer depends mostly on one package's local behavior, move to
that package handbook instead of treating the repository root as a second
owner.

## What This Page Answers

- which repository-level schema decision is in scope
- which shared assets or workflows deserve inspection
- how repository governance stops before package-local ownership

## Reviewer Lens

- compare the page claims with the real root files, workflows, or schema assets
- check that repository guidance still stops where package ownership begins
- confirm that any repository rule described here is still enforceable in code or automation

## Honesty Boundary

Repository guidance here does not override package-local ownership. The real
backstops are the referenced files, workflows, schemas, and checks.

## Next Checks

- move to the owning package docs when the question stops being repository-wide
- check root files, schemas, or workflows named here before trusting prose alone
- use the maintainer handbook at `https://bijux.io/bijux-canon/07-bijux-canon-maintain/`
  when the root issue is really about automation or drift tooling

## Purpose

Schemas are first-class repository assets here because cross-package review
depends on them being visible, diffable, and validated outside package source
alone.

## Stability

Keep this page aligned with the actual schema directories and the validation tooling that protects them.
