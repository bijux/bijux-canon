---
title: Operations
audience: mixed
type: index
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-26
---

# Operations

The operations section explains how the repository is run, reviewed, and kept
coherent once the ownership model is already clear. These pages cover
repeatable root-level procedure: local setup, validation, schema review,
artifact handling, release flow, and change acceptance across the package set.

## Visual Summary

```mermaid
flowchart LR
    change["repository change<br/>shared work at the root"]
    setup["local development<br/>environment and command entrypoints"]
    validation["validation<br/>tests, schemas, automation checks"]
    release["release and artifacts<br/>versioning and publication"]
    review["review posture<br/>acceptance and change management"]
    change --> setup
    setup --> validation
    validation --> release
    validation --> review
    release --> review
    classDef page fill:var(--bijux-mermaid-page-fill),stroke:var(--bijux-mermaid-page-stroke),color:var(--bijux-mermaid-page-text),stroke-width:2px;
    classDef positive fill:var(--bijux-mermaid-positive-fill),stroke:var(--bijux-mermaid-positive-stroke),color:var(--bijux-mermaid-positive-text);
    classDef caution fill:var(--bijux-mermaid-caution-fill),stroke:var(--bijux-mermaid-caution-stroke),color:var(--bijux-mermaid-caution-text);
    class change page;
    class setup,validation,release positive;
    class review caution;
```

## Start Here

- open [Contributor Workflows](contributor-workflows.md) for the shortest route through normal repository work
- open [Testing and Validation](testing-and-validation.md) when the question is which shared proof must run before acceptance
- open [API and Schema Governance](api-and-schema-governance.md) when the concern is contract drift or reviewed schema change
- open [Release and Versioning](release-and-versioning.md) when the concern is tag behavior, package publication, or release discipline
- open [Automation Surfaces](automation-surfaces.md) when the question is which shared root automation owns the current action

## Pages in This Section

- [Local Development](local-development.md)
- [Testing and Validation](testing-and-validation.md)
- [Release and Versioning](release-and-versioning.md)
- [API and Schema Governance](api-and-schema-governance.md)
- [Contributor Workflows](contributor-workflows.md)
- [Automation Surfaces](automation-surfaces.md)
- [Artifact Governance](artifact-governance.md)
- [Review Expectations](review-expectations.md)
- [Change Management](change-management.md)

## Use This Section When

- you are performing repository-wide work instead of one package-local change
- you need the operational truth for shared automation, release, or validation
- you are checking whether a proposed workflow is explicit enough to maintain

## Do Not Use This Section When

- the real question is still why the split exists or where authority changes
  hands
- you already know the issue belongs in one package's local operations docs
- you need maintainer-helper implementation detail rather than repository
  procedure

## Concrete Anchors

- `Makefile` and `makes/` for shared command entrypoints
- `.github/workflows/` for repository-wide automation and release execution
- `apis/` for schema governance surfaces that affect shared review
- [Testing and Validation](testing-and-validation.md) and
  [Artifact Governance](artifact-governance.md) for the highest-cost shared
  review surfaces

## Read Across The Repository

- open [Foundation](../foundation/index.md) when an operational problem is really a boundary problem
- open [Maintainer Handbook](../../07-bijux-canon-maintain/index.md) when the question becomes workflow implementation, drift tooling, or maintainer helper code
- open the owning package handbook when the operation is no longer truly shared

## Operational Standard

Shared procedure must be discoverable from checked-in rules, commands, and
workflow files. If a repository-wide action still depends on CI archaeology or
private habit, the operational surface is not documented strongly enough yet.
