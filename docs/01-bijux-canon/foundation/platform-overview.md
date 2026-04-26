---
title: Platform Overview
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-04
---

# Platform Overview

`bijux-canon` is a multi-package system because the work is easier to reason
about when preparation, retrieval, reasoning, orchestration, and runtime
governance stay distinct. The split is not cosmetic. It is the main mechanism
that keeps ownership explicit and review conversations short.

Read the platform as a pipeline of responsibilities rather than a stack of
directories. Ingest prepares deterministic material. Index turns retrieval
behavior into an executable contract. Reason shapes evidence-backed claims.
Agent coordinates role-local behavior and traceable runs. Runtime owns
execution, replay, and acceptance authority across the wider flow.

That design pays off in review. A reader can ask a sharper question sooner:
is this change about preparing material, executing retrieval, reasoning from
evidence, orchestrating work, or governing runtime outcomes? The repository
is healthier when that question has one obvious answer instead of five partial
ones.

## Visual Summary

```mermaid
flowchart LR
    ingest["Ingest<br/>prepare deterministic material"]
    index["Index<br/>execute retrieval and provenance"]
    reason["Reason<br/>form inspectable claims"]
    agent["Agent<br/>coordinate role-based work"]
    runtime["Runtime<br/>govern execution and replay"]
    ingest --> index --> reason --> agent --> runtime
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class ingest,index,reason,agent positive;
    class runtime page;
```

## What the Repository Provides

- publishable Python distributions under `packages/`
- shared API schemas under `apis/`
- root automation through `Makefile`, `makes/`, and CI workflows
- one canonical documentation system under `docs/`

## What the Repository Does Not Try to Be

- a single import package with one root `src/` tree
- a place where repository glue silently overrides package ownership
- a documentation mirror that drifts away from the checked-in code

## Concrete Anchors

- `pyproject.toml` for workspace metadata and commit conventions
- `Makefile` and `makes/` for root automation
- `apis/` and `.github/workflows/` for schema and validation review

## Open This Page When

- you are dealing with repository-wide seams rather than one package alone
- you need shared workflow, schema, or governance context before changing code
- you want the monorepo view that sits above the package handbooks

## Decision Rule

Open this page when the main need is understanding how the canonical packages
fit together. If the answer depends mostly on one package's local behavior,
open that package handbook instead of stretching the repository overview
past its boundary.

## What You Can Resolve Here

- which package owns which part of the system
- which shared repository assets support the package split
- how the repository overview differs from package-local ownership

## Review Focus

- compare the page claims with the real root files, workflows, or schema assets
- check that repository guidance still stops where package ownership begins
- confirm that any repository rule described here is still enforceable in code or automation

## Limits

This overview explains the split between packages, but package-local docs,
code, schemas, and tests still provide the detailed proof.

## Read Next

- open the owning package docs when the question stops being repository-wide
- check root files, schemas, or workflows named here before trusting prose alone
- use the package handbooks at `https://bijux.io/bijux-canon/02-bijux-canon-ingest/`
  through `https://bijux.io/bijux-canon/06-bijux-canon-runtime/` when the
  question narrows to one package

