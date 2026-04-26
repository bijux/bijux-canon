---
title: Repository Handbook
audience: mixed
type: index
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Repository Handbook

The repository handbook explains the shared story above the package level:
why this repository is split, which rules genuinely live at the root, and how
the packages stay coordinated without collapsing back into one blurry codebase.

`bijux-canon` is easiest to understand if you start from intent instead of
from filenames. The repository exists to keep several deterministic,
reviewable surfaces moving together: ingest prepares evidence, index makes
retrieval executable, reason makes claims inspectable, agent turns role-based
work into orchestrated runs, and runtime decides what execution and replay
results are acceptable.

The repository is therefore less like a toolbox and more like a chain of
accountable boundaries. Each package is meant to carry one kind of promise
clearly enough that readers do not have to reverse-engineer the whole tree to
understand where authority lives.

<div class="bijux-callout"><strong>The root is a coordination layer, not a shadow owner.</strong>
Product behavior should stay inside the publishable packages under `packages/`.
The root only owns what is genuinely shared: workspace layout, schema
governance, documentation rules, validation posture, and release
coordination.</div>

These repository pages should explain the cross-package frame that no single
package can explain alone. They are strongest when they make the monorepo
easier to understand without turning the root into a second owner of package
behavior.

## Visual Summary

```mermaid
flowchart LR
    reader["reader question<br/>is this rule shared or package-local?"]
    foundation["Foundation<br/>split, scope, ownership, language"]
    operations["Operations<br/>development, validation, release, review"]
    packages["Product handbooks<br/>package-owned behavior"]
    maintain["Maintainer handbook<br/>repository automation and drift control"]
    reader --> foundation
    reader --> operations
    foundation --> packages
    operations --> packages
    operations --> maintain
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    classDef anchor fill:var(--bijux-mermaid-anchor-fill),stroke:var(--bijux-mermaid-anchor-stroke),color:var(--bijux-mermaid-anchor-text);
    classDef action fill:var(--bijux-mermaid-action-fill),stroke:var(--bijux-mermaid-action-stroke),color:var(--bijux-mermaid-action-text);
    class reader page;
    class foundation positive;
    class operations anchor;
    class packages action;
    class maintain caution;
```

## Start Here

- open [Foundation](foundation/index.md) when the question is why the split
  exists or where authority changes hands
- open [Operations](operations/index.md) when the question is how repository
  work is validated, released, or reviewed
- move straight to a product handbook when the real issue is already local to
  one package boundary
- move to [Maintainer Handbook](../07-bijux-canon-maintain/index.md) when the
  concern is CI, workflow fan-out, generated docs checks, or repository-health
  automation

## Sections

- [Foundation](foundation/index.md) for the repository split, ownership model,
  shared language, and design rules that should stay stable over time
- [Operations](operations/index.md) for contributor workflows, validation,
  release, automation, artifact handling, and shared review posture

## What This Handbook Owns

- the shared explanation of why the root exists at all
- repository-wide workflow, validation, release, and artifact rules
- the seams where one package hands authority to another

## What This Handbook Does Not Own

- ingest, index, reason, agent, or runtime behavior inside the package docs
- maintainer-helper implementation detail that belongs in the maintainer
  handbook
- legacy package naming that belongs in compatibility docs

## Shared Package Map

- `bijux-canon-ingest` for deterministic document ingestion, chunking, retrieval assembly, and ingest-facing boundaries.
- `bijux-canon-index` for contract-driven vector execution with replay-aware determinism, audited backend behavior, and provenance-rich result handling.
- `bijux-canon-reason` for deterministic evidence-aware reasoning, claim formation, verification, and traceable reasoning workflows.
- `bijux-canon-agent` for deterministic, auditable agent orchestration with role-local behavior, pipeline control, and trace-backed results.
- `bijux-canon-runtime` for governed execution and replay authority with auditable non-determinism handling, persistence, and package-to-package coordination.

## Concrete Anchors

- `pyproject.toml` for workspace metadata and commit conventions
- `Makefile` and `makes/` for root automation
- `apis/` and `.github/workflows/` for schema and validation review
- `packages/` for the product boundaries this handbook must not blur

## Use This Page When

- you are dealing with repository-wide seams rather than one package alone
- you need shared workflow, schema, or governance context before changing code
- you want the monorepo view that sits above the package handbooks

## Do Not Use This Page When

- the answer depends mostly on one package's local behavior, imports, or tests
- you need workflow automation internals rather than root-facing guidance
- the question is explicitly about a legacy name and migration path

## Read The Root This Way

Treat the root as a coordination layer, not a shadow product. The repository handbook should tell you why the split exists, what rules stay shared, and when to leave the root immediately because the real authority lives inside a package. If the root starts to explain package behavior in detail, the handbook is crossing its own boundary.

## Reader Takeaway

Use this handbook when the question is genuinely shared across package boundaries. If the current issue can be explained honestly inside one product handbook, this root should route you there instead of trying to keep you.

## Purpose

This page gives the shortest credible explanation of why the monorepo exists and what kind of questions belong in the repository handbook instead of a package handbook.

## Stability

This page is part of the canonical docs spine. Keep it aligned with the current repository layout and the actual package set declared in `pyproject.toml`.
