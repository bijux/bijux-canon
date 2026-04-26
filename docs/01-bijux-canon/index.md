---
title: Repository Handbook
audience: mixed
type: index
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Repository Handbook

Open the repository handbook when the question belongs to the part of
`bijux-canon` that no single package owns alone: why the split exists, which
rules belong at the root, and how package handoffs stay explicit across the
repository.

<div class="bijux-callout"><strong>The root is a coordination layer, not a shadow owner.</strong>
Product behavior belongs in the publishable packages under `packages/`.
The root only owns what is genuinely shared: workspace layout, schema
governance, documentation rules, validation posture, and release
coordination.</div>

## Visual Summary

```mermaid
flowchart TB
    root["repository root<br/>shared governance and coordination"]
    foundation["foundation<br/>split, scope, ownership, language"]
    operations["operations<br/>workflow, validation, release, review"]
    packages["canonical packages<br/>owned product behavior"]
    maintain["maintainer handbook<br/>helper code, make, workflows"]
    compat["compatibility handbook<br/>legacy names and migration"]
    root --> foundation
    root --> operations
    foundation --> packages
    operations --> packages
    operations --> maintain
    foundation --> compat
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class root page;
    class foundation positive;
    class operations anchor;
    class packages action;
    class maintain caution;
    class compat caution;
```

## Start Here

- open [Foundation](https://bijux.io/bijux-canon/01-bijux-canon/foundation/) for repository shape, split logic, ownership boundaries, and shared terminology
- open [Operations](https://bijux.io/bijux-canon/01-bijux-canon/operations/) for contributor workflow, validation posture, release flow, and review rules
- open a product handbook as soon as the behavior is clearly local to one canonical package
- open the [Maintenance Handbook](https://bijux.io/bijux-canon/07-bijux-canon-maintain/) when the concern is helper code, Make routing, workflow fan-out, or repository-health automation
- open the [Compatibility Handbook](https://bijux.io/bijux-canon/08-compat-packages/) only when a legacy package name or migration question is still active

## Choose A Section

- [Foundation](https://bijux.io/bijux-canon/01-bijux-canon/foundation/) for the repository split, ownership model,
  shared language, and design rules that should stay stable over time
- [Operations](https://bijux.io/bijux-canon/01-bijux-canon/operations/) for contributor workflows, validation,
  release, automation, artifact handling, and shared review posture

## What This Handbook Owns

- the reason the repository is split into canonical packages instead of one combined surface
- root-owned workflow, validation, release, artifact, and documentation rules
- the seams where one package hands authority to another package or to a shared root rule

## What This Handbook Does Not Own

- ingest, index, reason, agent, or runtime behavior inside the product handbooks
- helper implementation detail that belongs in the maintainer handbook
- legacy-name migration policy that belongs in the compatibility handbook

## Shared Package Map

- `bijux-canon-ingest` prepares source material for deterministic downstream use.
- `bijux-canon-index` executes retrieval and records provenance-rich result state.
- `bijux-canon-reason` turns retrieved evidence into inspectable claims and verification outputs.
- `bijux-canon-agent` coordinates role-based orchestration without hiding traces or package boundaries.
- `bijux-canon-runtime` governs execution, replay, persistence, and final acceptability.

## Check The Root Files

- `pyproject.toml` for workspace metadata and commit conventions
- `Makefile` and `makes/` for root automation
- `apis/` and `.github/workflows/` for schema and validation review
- `packages/` for the product boundaries this handbook must not blur

## Open This Handbook When

- you are dealing with repository-wide seams rather than one package alone
- you need shared workflow, schema, or governance context before changing code
- you want the monorepo view that sits above the package handbooks

## Open Another Handbook When

- the answer depends mostly on one package's local behavior, imports, or tests
- you need workflow automation internals rather than root-facing guidance
- the work is explicitly about a legacy name and migration path

## Read The Root This Way

Treat the root as a coordination layer. Use these pages to understand why the
split exists, which rules stay shared, and where authority changes hands.
Once the behavior is package-local, open the owning package handbook instead
of keeping the explanation at the root.

## Cross-Package Anchors

- `pyproject.toml` declares the workspace and package set
- `mkdocs.yml` defines the published handbook structure
- `Makefile`, `makes/`, and `.github/workflows/` carry root-level operations
- `packages/` carries the canonical product boundaries the root must not blur
